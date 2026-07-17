---
id: SPEC-004
title: "Ref decoration: branch, tag, and HEAD labels on the commit graph"
category: feature
owner: achim.daeubler                         # git config user.name
authored_by: augmented                # augmented | automated
---

## Problem statement

The commit-graph viewer (SPEC-001/002/003) renders commits, lanes, and a
detail panel, but every commit looks anonymous: there is no way to tell which
commit is the tip of `main`, which is a feature branch, where a tag points, or
which commit `HEAD` is on. SPEC-002 made commits from all branches *visible*
but explicitly deferred **ref decoration** (labels naming the branches, tags,
and HEAD) to a later spec — this is that spec.

Without labels, the all-refs view is hard to read: a developer sees several
parallel lanes but cannot map a lane to a branch name, cannot spot a release
tag, and cannot find "where am I right now" (HEAD). Ref decoration is the
single most identifying piece of information in every graph tool (git's own
`git log --decorate`, GitLab/GitHub graph panes, gitk). This spec adds it:
each commit that a ref points **directly** at shows that ref's name as a
labeled badge next to its node, visually distinguishing local branches,
remote-tracking branches, tags, and HEAD.

## Acceptance criteria

<!-- Numbered, testable criteria. Each describes an observable outcome, not an implementation step. -->

1. `GET /api/commits` includes, for every commit in the returned window, a
   `refs` array. Each entry is an object with `name` (string, the short ref
   name — e.g. `main`, `origin/main`, `v1.0`, not the full `refs/heads/main`),
   `type` (one of `branch`, `remote`, `tag`, `head`), and `is_head` (bool).
   Commits that no ref points at have an empty `refs` array.
2. A ref decorates **only the single commit it points directly at** (the ref
   tip), matching `git log --decorate` semantics — not every commit reachable
   from it. Verified against `git for-each-ref` / `git show-ref` on the golden
   fixtures: the set of `(commit_sha, ref_name)` pairs the API reports equals
   the set git reports, restricted to commits in the returned window.
3. Local branches appear with `type: "branch"` and their short name
   (`refs/heads/main` → `main`); remote-tracking branches appear with
   `type: "remote"` and their short name (`refs/remotes/origin/main` →
   `origin/main`); tags appear with `type: "tag"` and their short name
   (`refs/tags/v1.0` → `v1.0`). Annotated tags decorate the commit they
   ultimately peel to. `refs/remotes/*/HEAD` symbolic refs are excluded (they
   are aliases, not tips).
4. HEAD is represented: when `HEAD` is symbolic (attached to a branch), the
   commit at that branch tip carries both the branch entry AND has that
   branch entry's `is_head: true` (so the UI can render `HEAD → main`). When
   `HEAD` is detached, the commit it points at carries a dedicated entry
   `{name: "HEAD", type: "head", is_head: true}`.
5. In the rendered graph, a commit with one or more refs shows a labeled badge
   per ref immediately to the right of its node (before or inline with the
   commit subject). Each badge shows the ref `name`. A commit with no refs
   shows no badge and its row layout is otherwise unchanged from SPEC-001.
6. Badges are visually distinguishable by type: local branch, remote branch,
   tag, and HEAD each have a distinct style (e.g. color/shape/icon or prefix),
   and the distinction does not rely on color alone (a text/shape cue is also
   present, for accessibility). The HEAD indicator is visually emphasized.
7. Ref decoration is computed for commits regardless of walk mode: even in the
   default HEAD-only mode (`refs: "head"`), a decorated commit that is present
   in the window (e.g. the HEAD-tip commit carrying `main` and `HEAD`) shows
   its labels. Refs whose tip commit falls outside the returned window
   (truncated by the cap or unreachable in the current mode) simply do not
   appear — no dangling or fabricated labels.
8. Reading ref decoration performs no writes: no refs are created/updated, no
   objects added, no working tree or index change. Verified by a `.git/`
   before/after snapshot-equality test around the `/api/commits` fetch.
9. `README.md` documents ref decoration: what the badges mean, the four ref
   types, the `HEAD → branch` indicator, and the per-commit `refs` field shape
   in the API section. Documented behavior succeeds on a clean checkout.
10. Backward compatibility: the existing `/api/commits` response keeps all
    current fields (`repo`, `max_commits`, `refs` top-level mode string,
    `count`, `lane_count`, `commits[]` with `sha`/`lane`/`color`/`edges`/…);
    the per-commit `refs` array is purely additive. Existing SPEC-001/002/003
    tests continue to pass unchanged.

## Research

Extends SPEC-001/002/003 (all `done`, merged to `main`). Prior learnings come
from `.spec/_ledger/{git-reader,architecture}.yaml` and those specs'
`meta.yaml`.

- **This is the ref-decoration work SPEC-001 and SPEC-002 explicitly
  deferred.** SPEC-002's `future_work` learning names branch-aware labels as
  the UX fix for "which branch is this lane?"; colors stay lane-based (not
  ref-based) — decoration adds tip badges only, it does not recolor lanes or
  nodes. (learnings-curator)
- **Decoration is a separate tip-SHA→refs map, computed regardless of walk
  mode.** The existing `_tip_oids` peel/skip idiom (`app/git_reader.py`
  lines 127–164) is the pattern to reuse, but its `if not all_refs: return`
  gate must NOT be reused — decoration must enumerate refs even in HEAD-only
  mode (AC-7), then intersect against the returned window. Refs whose tip is
  outside the window are silently omitted, mirroring SPEC-001's boundary-edge
  "no dangling reference" rule. (repo-analyst, learnings-curator,
  prior-art-researcher)
- **Server computes, frontend renders — and it threads through cleanly.**
  `CommitRecord.to_dict()` is `asdict(self)` and `build_graph` passes
  `commit.to_dict()` straight through (`app/graph.py` line 97), so adding
  `refs: list[dict] = field(default_factory=list)` to `CommitRecord` flows to
  `/api/commits` with **zero graph changes**. `app/graph.py` stays untouched
  (regression assertion only). (repo-analyst, learnings-curator)
- **Tip-only decoration is the cross-tool consensus (`git log --decorate`).**
  A ref labels only the commit it points directly at, not reachable history
  (`--decorate`/`%d`, distinct from `git branch --contains`). Annotated tags
  decorate the peeled commit. This is the oracle for AC-2/AC-3. (docs-researcher,
  prior-art-researcher)
- **pygit2 API (confirmed).** Enumerate via `repo.references` prefix-filtered
  by `refs/heads/`, `refs/remotes/`, `refs/tags/`; peel each with
  `Reference.peel(pygit2.Commit)` (recursive; handles annotated + tag-of-tag);
  wrap in try/except to skip tag-of-tree/blob and dangling refs. Get short
  names from `Reference.shorthand` (`refs/heads/main`→`main`,
  `refs/remotes/origin/main`→`origin/main`, `refs/tags/v1.0`→`v1.0`) rather
  than manual stripping; derive `type` from the namespace. HEAD:
  `repo.head_is_detached` → dedicated `{name:"HEAD", type:"head",
  is_head:true}`; else mark the matching local-branch entry `is_head:true`
  (short name via `repo.head.shorthand`). Skip symbolic
  `refs/remotes/*/HEAD` (aliases, not tips) by name/`ReferenceType.SYMBOLIC`.
  Use `pygit2.enums.*` (top-level `GIT_*` constants are removed in 1.20).
  (docs-researcher)
- **git CLI fallback (one pass).** `git for-each-ref
  --format='%(objectname)%00%(refname:short)%00%(*objectname)%00%(objecttype)%00%(*objecttype)'
  refs/heads refs/remotes refs/tags` — pick `*objectname` when `*objecttype`
  is `commit` (annotated tag, peeled), else `objectname` when `objecttype` is
  `commit`, else skip. Resolve HEAD with `git symbolic-ref -q --short HEAD`
  (attached → branch name; detached → exit 1) and `git rev-parse HEAD`
  (detached commit SHA). All are read-only plumbing (packed + loose refs
  covered). **Corrects a drafting typo:** the third format field is
  `%(*objectname)` (peeled), not a duplicate `%(objectname)`. Use git's
  `%x00`/`%00` NUL escape in the format string, not a literal NUL in argv
  (SPEC-003 Windows `CreateProcess` gotcha), and scope any subprocess env via
  `env=` per `.cursor/rules/shell-env-hygiene.mdc`. (docs-researcher,
  learnings-curator)
- **Badge order is a convention, not an oracle.** Git has no universal
  type-sort — it uses refname/insertion order with only the `HEAD → branch`
  collapse special-cased. So the git-oracle test must assert the
  `(commit_sha, ref_name)` **set** (AC-2), not ordering. The spec's
  HEAD→branch→remote→tag badge order is a deterministic UI choice; render
  `HEAD → main` as a combined indicator (attached), a bare emphasized `HEAD`
  (detached — badge alone is easy to miss, so emphasize it). (prior-art-researcher)
- **Type badges disambiguate; non-color cue is required.** A branch and a tag
  can share a short name on one commit (a real footgun in other tools), so the
  typed badge is what disambiguates — reinforcing AC-6's "not color alone"
  (Git uses a `tag:` text prefix; Tig uses bracket shapes; GitLens uses icons).
  (prior-art-researcher)
- **Dual-backend parity is essential and historically weak here.** SPEC-003
  found the SPEC-001 CLI fallback was never exercised by tests. Decoration
  must test both backends (parametrize or patch out pygit2) and assert against
  a `git for-each-ref`/`git show-ref -d` oracle. `.git/` before/after snapshot
  equality proves AC-8, following the SPEC-003 read-only test pattern
  (`tests/test_git_reader.py`). (learnings-curator, docs-researcher)
- **Test/fixture reality (repo-analyst).** `RepoBuilder` already has
  `tag(name, annotated=)`, a `remote_tracking_repo` fixture (real
  `refs/remotes/up/*`), and a `tagged_side_history_repo`; the one gap is a
  **detached-HEAD helper** (add `git switch --detach`/`checkout <sha>`).
  Adding `refs` with a list default is regression-safe: `test_graph.py`'s `_c`
  helper uses positional `CommitRecord` args, and
  `test_api.py::test_list_endpoint_shape_unchanged` asserts the **exact
  top-level key set** `{repo, max_commits, count, lane_count, commits, refs}`
  — the per-commit `refs` array lives under `commits[]`, so it doesn't touch
  that assertion. Note the naming overlap: top-level `refs` is the walk-mode
  string (`"head"`/`"all"`), per-commit `refs` is the decoration array — same
  key name, different nesting; call it out in README/API docs. (repo-analyst)
- **Frontend layout needs real work.** `web/app.js` `render()` uses fixed
  offsets (sha at `textX`, subject at `textX + 64`); variable-width badges
  between the node and the subject require a dynamic subject `x` (measured
  badge-group width) or a dedicated badge column. Badge elements must set
  `pointer-events: none` like `.sha`/`.subject` so row clicks still hit
  `.row-hit` (SPEC-003 detail-panel interaction). Long ref names are a known
  crowding/truncation pain point in graph UIs — truncate with a title/tooltip.
  (repo-analyst, prior-art-researcher)

## Scope boundaries

Explicitly OUT of scope (candidates for later specs):

- **Filtering / toggling refs in the UI** (show/hide tags, hide remotes, pick a
  branch to focus). Decoration is display-only; mode remains startup-config.
- **Clicking a badge to check out / navigate / filter** — badges are labels,
  not controls (a later interaction spec may add this).
- **Ref decoration inside the commit detail panel** (SPEC-003) — this spec
  decorates the graph rows only; adding refs to the detail payload is deferred.
- **Ordering/prioritizing multiple badges** beyond a stable, deterministic
  order (e.g. HEAD first, then branches, then remotes, then tags) — no
  user-configurable badge ordering.
- **Ref counts / "N more refs" collapsing** when a commit has many refs — all
  refs are rendered; a collapse affordance is a later polish spec.
- Writing to the repository in any way (hard read-only NFR, carried forward).

## User scenarios

- **Finding the current branch:** A developer opens the graph and immediately
  sees `HEAD → main` on the top commit, confirming where they are before
  starting work.
- **Mapping lanes to branches:** In all-refs mode, a developer sees each lane's
  tip labeled (`feature/login`, `origin/main`, `v2.1`), turning an anonymous
  set of parallel lanes into a readable branch/tag map.
- **Spotting releases:** A developer scans for tag badges to locate release
  points in the history.

## Non-functional requirements

- **Read-only:** ref enumeration must not mutate the target repository (refs,
  objects, index, working tree). Hard NFR carried from SPEC-001.
- **Responsiveness:** computing decoration must not materially regress
  `/api/commits` latency; ref enumeration is O(refs) and a single pass to map
  tip-SHA → refs, independent of the commit cap.
- **Cross-platform:** works under both the `pygit2` backend and the `git`
  subprocess fallback, on Windows/macOS/Linux (matches SPEC-001).
- **Accessibility:** badge type distinction does not rely on color alone
  (AC-6); badges have accessible text.

## Implementation guidance

This is an additive change to the reader's output and the frontend renderer.
Keep ref enumeration in the reader (server computes, frontend renders — the
ledger `architecture.yaml` pattern), and pass refs through `build_graph`
untouched.

- **Files likely affected:**
  - `app/git_reader.py` — add a ref-decoration map builder that returns
    `dict[str, list[dict]]` (full-commit-SHA → list of `{name, type, is_head}`)
    for the repo, for both backends:
    - **pygit2:** iterate `repo.references`; for each `refs/heads/*`,
      `refs/remotes/*` (skip `.../HEAD` symbolic aliases, e.g. by
      `ReferenceType.SYMBOLIC` or name), and `refs/tags/*`, peel with
      `Reference.peel(pygit2.Commit)` and record `(commit.id, {name, type})`
      where `name` comes from `Reference.shorthand` and `type` from the
      namespace. Resolve `HEAD`: if `repo.head_is_detached`, add
      `{name:"HEAD", type:"head", is_head:true}` on the HEAD commit; else mark
      the matching local-branch entry `is_head:true` (short name via
      `repo.head.shorthand`). Reuse the peel/skip try/except from `_tip_oids`
      (lines 127–164) but NOT its `all_refs` gate — decoration runs always.
    - **git CLI fallback:** one pass, `git for-each-ref
      --format='%(objectname)%00%(refname:short)%00%(*objectname)%00%(objecttype)%00%(*objecttype)'
      refs/heads refs/remotes refs/tags` — use `*objectname` when
      `*objecttype == commit` (annotated tag, peeled), else `objectname` when
      `objecttype == commit`, else skip. Skip `refs/remotes/*/HEAD` by name.
      Resolve HEAD with `git symbolic-ref -q --short HEAD` (attached → branch;
      exit 1 → detached) + `git rev-parse HEAD` (detached SHA). Use git's
      `%x00` NUL escape in the format (not a literal NUL in argv — SPEC-003
      Windows gotcha) and scope env via `env=` per
      `.cursor/rules/shell-env-hygiene.mdc` (as `_read_commit_detail_git` does).
    - Attach the per-commit `refs` list onto each `CommitRecord`'s output. The
      cleanest seam: have `read_commits` return the decoration map alongside
      records, OR add an optional `refs` field to `CommitRecord`. Prefer adding
      `refs: list[dict]` to `CommitRecord` (defaulted empty) so `to_dict()`
      carries it through `build_graph` with no graph change.
  - `app/graph.py` — **no logic change**; `build_graph` already passes
    `commit.to_dict()` through, so a new `refs` field flows to the API
    automatically. Confirm and add a regression assertion only.
  - `app/server.py` — `/api/commits` already serializes `graph["commits"]`;
    ensure the `refs` field is populated on each commit dict. No new route.
  - `web/app.js` — in `render()`'s per-row loop (lines 113–136), after the node
    circle, render a badge group per `c.refs` entry between the node area and
    the subject text (shift the subject `x` right by the badges' measured
    width, or render badges in a dedicated column). Style by `type` and
    `is_head`. Keep existing `sha`/`subject`/`meta` text.
  - `web/styles.css` — add `.ref-badge` and per-type modifiers
    (`.ref-branch`, `.ref-remote`, `.ref-tag`, `.ref-head`) using the existing
    palette variables; ensure a non-color cue (prefix glyph/border/shape).
  - `web/index.html` — no structural change expected (badges are SVG within the
    existing graph); touch only if a legend is added.
  - `README.md` — document badges, ref types, `HEAD → branch`, and the
    per-commit `refs` field (AC-9).
  - `tests/conftest.py` — `RepoBuilder` already has `tag(name, annotated=)`,
    a `remote_tracking_repo` fixture (real `refs/remotes/*`), and a
    `tagged_side_history_repo`; reuse them. Add the one missing helper — a
    **detached-HEAD** checkout (`git switch --detach <sha>`) and a fixture
    whose tip carries a mix of local branch + lightweight + annotated tag on
    one commit (multi-ref row) for AC-5/AC-6.
  - `tests/test_git_reader.py` — decoration map correctness vs `git show-ref` /
    `git for-each-ref`; tip-only semantics (AC-2); type mapping and short names
    (AC-3); HEAD attached vs detached (AC-4); annotated-tag peeling; `.git/`
    snapshot equality (AC-8); dual-backend parity (pygit2 + CLI).
  - `tests/test_api.py` — `/api/commits` per-commit `refs` shape (AC-1);
    empty `refs` for undecorated commits; existing response shape intact
    (AC-10 regression guard).
- **Files NOT to modify:**
  - `app/graph.py` lane algorithm internals — decoration is orthogonal;
    passthrough only (a regression assertion is fine).
  - `app/config.py` — no new startup surface (decoration is always computed).
  - Anything under `.cursor/` or `.spec/` outside this spec directory.
  - The **target** git repository (hard read-only NFR).
- **Patterns to follow:**
  - Dual-backend reader with a shared output shape (SPEC-001/003 precedent);
    both backends must produce identical decoration maps so tests parametrize.
  - Peel/skip idiom from `_tip_oids` for non-commit and symbolic refs.
  - Frozen dataclass + `to_dict()` passthrough (`CommitRecord`).
  - Server computes, frontend renders (ledger `architecture.yaml`).
  - Boundary convention: refs on out-of-window tips simply do not render
    (mirror the SPEC-001 boundary-edge "no dangling reference" rule).
- **Test expectations:**
  - `git`-oracle equality for the **set** of `(sha, ref_name)` decoration
    pairs on fixtures (AC-2/AC-3), restricted to the returned window — assert
    the set, not badge order (git has no universal type-sort).
  - HEAD attached (`is_head` on the branch) and detached (`HEAD` head entry)
    both covered (AC-4).
  - `.git/` directory snapshot equality around a decorated `/api/commits` read
    proves AC-8.
  - CLI-fallback path exercised (parametrization or pygit2 patched out),
    matching SPEC-003's dual-path discipline.
  - Regression: unchanged `/api/commits` top-level shape and existing
    SPEC-001/002/003 assertions (AC-10).
