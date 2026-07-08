---
id: SPEC-001
title: "Commit graph viewer (read local repo, render git graph)"
category: feature
owner: achim.daeubler                         # git config user.name
authored_by: augmented                # augmented | automated
---

## Problem statement

Developers exploring a git repository on their machine have no lightweight,
visual way to understand its branch/merge topology. `git log --graph` is
terminal-only and hard to read for non-trivial histories, and full platforms
like GitLab require hosting the repo remotely. This spec delivers the
foundational slice of a local git graph viewer: a web app that reads a git
repository from the local filesystem and renders its commit history as a
visual graph (commit nodes connected by branch/merge lines), similar to the
graph pane in GitLab/GitHub.

This first spec establishes the app shell (Python backend + web frontend),
the git-reading layer, the commit-graph lane-assignment algorithm, and the
graph rendering. Later specs build on it (commit details, ref decoration,
repo picker, search, large-repo performance).

## Acceptance criteria

<!-- Numbered, testable criteria. Each describes an observable outcome, not an implementation step. -->

1. Given a path to a valid local git repository, starting the app and opening
   its web UI in a browser displays a commit graph for that repository.
2. Each commit is rendered as a distinct node showing at least its abbreviated
   SHA (7 chars), the first line of its commit message (subject), the author
   name, and the authored date.
3. Commits are ordered to match the **default `git log` order** — reverse
   chronological by committer date with the parent-before-child guarantee (i.e.
   `git log -n <cap>` with no extra ordering flags; explicitly NOT
   `--topo-order`). The most recent commit appears at the top, and the ordering
   is verified equal to that `git log` invocation on the golden fixture repos.
4. Merge commits (2+ parents) and branching points are visually connected to
   all their parent commits by lines/edges, so the branch and merge structure
   is visible — not just a flat list.
5. Parallel lines of development are drawn in separate horizontal lanes with
   distinct colors, so concurrent branches do not overlap on the same lane.
6. A repository with a single linear history (no branches/merges) renders as a
   single straight column of nodes.
7. The backend exposes an HTTP endpoint (e.g. `GET /api/commits`) that returns
   the commit graph data as JSON, including for each commit: full SHA, parents
   (list of SHAs), subject, author name, author email, and authored timestamp.
8. Pointing the app at a path that is not a git repository (or does not exist)
   returns a clear, user-visible error rather than crashing or showing a blank
   page.
9. The commit list is bounded to a configurable maximum (default 500 most
   recent commits) so the endpoint stays responsive on large repositories;
   the limit is applied server-side.
10. A README documents how to install dependencies, point the app at a repo,
    and run it locally, and the documented steps succeed on a clean checkout.

## Research

Scope note: this is a greenfield repo — it contains only Creator process
scaffolding (`.cursor/`, `.spec/`) and no application code. There are no prior
`done` specs and no `.spec/_ledger/`, so no prior learnings apply
(learnings-curator, repo-analyst lanes). All findings below are external
evidence for a from-scratch build.

- **Git-reading layer — prefer `pygit2`, with a `git log` subprocess fallback.**
  `pygit2` (libgit2 bindings) reads commits fully in-process with no `git`
  binary and ships prebuilt Windows/macOS/Linux wheels (`pip install pygit2`,
  1.19.x, Python ≥3.11), satisfying the cross-platform NFR. `dulwich` is a
  pure-Python alternative but is bytes-heavy and beta. `GitPython` is **not**
  a no-shell option — it wraps the `git` CLI and needs `git` on `PATH`. A
  dependency-light alternative is shelling out to
  `git log --pretty=format:"%H%x00%P%x00%s%x00%an%x00%ae%x00%at"` and splitting
  on NUL — this yields exactly the AC-7 fields and matches `git log` ordering
  semantics precisely, at the cost of requiring `git` installed. Do **not**
  parse `git log --graph` output for data — `--graph` is human ASCII art.
  (docs-researcher)
- **AC-3 ordering — resolved to default `git log` order.** Git's *default*
  `git log` order is reverse-chronological (committer date) with the
  parent-before-child guarantee, and it is **not** the same as `--topo-order`
  (which reorders branched histories differently). AC-3 now pins this
  explicitly: implement `git log -n <cap>` with no extra ordering flags and
  assert equality against that invocation on golden fixtures. Mapping for the
  no-shell path: `pygit2` `SortMode.TOPOLOGICAL | SortMode.TIME` ≈ `--date-order`
  and `SortMode.NONE` ≈ reverse-chronological, so if strict `git log`-default
  parity is required the subprocess path is the safest match. Also note `%at` /
  `commit.author.time` is the *authored* timestamp (AC-2/AC-7), distinct from
  committer time (which drives ordering). (docs-researcher, prior-art-researcher)
- **Lane assignment is a greedy, newest-first column-reservation pass, not a
  general graph-layout optimizer.** Walk commits newest→oldest; keep a list of
  active columns/lanes; the first parent inherits the commit's column, extra
  parents claim free columns (or fuse), and freed columns are reused. This is
  the canonical approach in `git`'s `graph.c`, git-cola's Python `dag.py`, and
  the Gitamine algorithm. Best implementer references: the pvigier "Commit
  Graph Drawing Algorithms" write-up + Gitamine `commit-graph.ts` (clearest
  straight-lane algorithm), `git/graph.c` (ground truth for merges/octopus/
  truncation), and git-cola `dag.py` (production-shaped Python precedent).
  (prior-art-researcher)
- **Compute lanes server-side.** Since the Python backend already owns git
  reads and the AC-9 cap, computing lane + color per commit there (à la git-cola
  and historical GitLab, which shipped a precomputed `space`/lane index in JSON)
  makes acceptance tests deterministic and keeps the frontend a "dumb" renderer.
  Both server- and client-side are <1s for 500 commits (O(n) greedy + sort), so
  this is a determinism/testability call, not a performance one. (prior-art-researcher)
- **Bounded-window (AC-9) creates two specific pitfalls.** (1) Commits whose
  parents fall outside the 500-cap window look orphaned unless the layout
  synthesizes "continues off-screen" boundary edges — this is the intersection
  of AC-4 and AC-9 and is a known bug source in real viewers. (2) Lane/color
  assignment for a truncated window is inherently unstable across different caps
  unless deterministic tie-breaks (first-parent bias, stable column reuse) are
  fixed. (prior-art-researcher)
- **Frontend: avoid `@gitgraph/js` (archived 2019/2021); render from
  server-computed lanes.** `@gitgraph/js` is unmaintained and uses an imperative
  branch API that does not accept a `{sha, parents[]}` graph — wrong shape for
  `/api/commits`. Actively maintained React options exist (`git-graph-svg`,
  `@tomplum/react-git-log`) but are young/React-only. For minimal, framework-light,
  cross-platform control, drawing SVG/Canvas directly from the server-provided
  `{sha, parents, lane, color}` is the lowest-risk path and matches how git-cola/
  GitLab historically rendered. (docs-researcher, prior-art-researcher)
- **Color: cycle a fixed palette by lane index, reuse on lane recycle.** This is
  the dominant pattern (`git graph.c`, VS Code git-graph family, GitLab). For
  AC-5's "distinct colors", an Okabe–Ito colorblind-safe categorical palette (8
  hues) is a good default; lanes beyond the palette cycle, with lane *position*
  disambiguating. Accessibility is not an AC here but the palette choice is free.
  (prior-art-researcher)

## Scope boundaries

Explicitly OUT of scope for this spec (candidates for later specs):

- Commit detail view / full message / diff display (later spec).
- Branch, tag, and HEAD ref labels/decoration on nodes (later spec).
- In-UI repo picker or opening arbitrary repos at runtime; the repo path is
  provided at startup via config/argument (later spec).
- Commit search, filtering, or author filtering (later spec).
- Pagination / infinite scroll / virtualized rendering beyond the fixed cap in
  AC-9 (later spec).
- Writing to the repository in any way — this is strictly read-only.
- Authentication, multi-user, remote/hosted deployment, remote repo cloning.
- Diffs, blame, file tree browsing.

## User scenarios

- **Solo developer inspecting local history:** A developer clones or opens a
  project locally, starts the app pointed at that repo, and views the branch
  and merge structure visually in the browser to understand how the history
  evolved.
- **Reviewing a messy feature branch:** Before merging, a developer looks at
  the graph to see how a feature branch diverged from and rejoined the main
  line.

## Non-functional requirements

- Read-only: the app must never mutate the target repository.
- Responsiveness: the `/api/commits` endpoint returns within ~1s for a repo of
  a few thousand commits when capped per AC-9.
- Cross-platform: runs on Windows, macOS, and Linux (developer chose Python +
  web; the git-access library must be cross-platform).
- No global installs beyond documented dependencies; runnable from a clean
  virtual environment.

## Implementation guidance

This is a greenfield app; all files below are new. Keep the backend, the
lane-assignment algorithm, and the frontend renderer in separate modules so the
algorithm can be unit-tested in isolation.

- **Files likely affected (all new, suggested layout):**
  - `pyproject.toml` or `requirements.txt` — pin `pygit2` (and web framework);
    document the `git log` subprocess fallback if pygit2 is unavailable.
  - `app/git_reader.py` — read commits from a local repo path via `pygit2`
    (`Repository.walk(head, SortMode…)`), producing raw commit records
    (full SHA, parents list, subject, author name/email, authored unix ts).
    Apply the AC-9 server-side cap (default 500) here.
  - `app/graph.py` — pure lane-assignment algorithm: greedy newest-first
    column reservation, first-parent-inherits-column, free-column reuse,
    octopus-merge handling, and boundary-parent edge synthesis for the AC-9
    window. Takes commit records, returns `{sha, parents, lane, color, edges}`.
    Deterministic (fixed tie-breaks) so tests are stable.
  - `app/server.py` — web app (FastAPI or Flask) exposing `GET /api/commits`
    (JSON per AC-7 + lane/color) and serving the static frontend; repo path via
    startup config/arg (AC-1, AC-8 error handling for missing/invalid repo).
  - `web/` (`index.html`, JS/CSS) — render nodes + branch/merge edges as SVG/
    Canvas from the server payload; newest-first top-down (AC-3), lane colors
    (AC-5), linear-history single column (AC-6).
  - `README.md` — install deps, point at a repo, run locally (AC-10).
  - Test fixtures: small golden repos (linear, branched+merged, octopus,
    truncated-beyond-cap) plus `tests/`.
- **Files NOT to modify:** anything under `.cursor/` and `.spec/` (Creator
  process scaffolding); do not modify or write to the *target* git repository —
  read-only is a hard NFR.
- **Patterns to follow:**
  - Lane algorithm: model on the pvigier/Gitamine straight-lane approach and
    `git/graph.c` semantics; git-cola `dag.py` is the closest Python precedent.
  - Ordering: choose one ordering explicitly (default `git log` vs
    `SortMode.TOPOLOGICAL | SortMode.TIME`) and assert it against `git log`
    output on the golden fixtures (resolves the AC-3 ambiguity noted in Research).
  - Serving: FastAPI `StaticFiles` mount or Flask `static/` + `jsonify`; run via
    `uvicorn`/`fastapi dev` or `flask run` — document the exact command in README.
- **Test expectations:**
  - `app/graph.py` unit tests on fixtures: linear→single lane (AC-6); a merge
    commit connects to all parents (AC-4); parallel branches occupy distinct
    lanes/colors (AC-5); commits with parents outside the cap get boundary edges,
    not dangling references (AC-4 + AC-9).
  - API test: `GET /api/commits` returns the AC-7 fields, newest-first (AC-3),
    capped at the configured max (AC-9), and a clear error (not a crash/blank)
    for a non-repo/missing path (AC-8).
  - Ordering test asserting equivalence to the chosen `git log` invocation on a
    branched fixture.
  - README steps verified to succeed on a clean virtual environment (AC-10).
