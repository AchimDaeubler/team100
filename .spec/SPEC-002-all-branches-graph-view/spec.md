---
id: SPEC-002
title: "All-branches / all-refs commit graph view"
category: feature
owner: celvink                         # git config user.name
authored_by: augmented                # augmented | automated
---

## Problem statement

The commit graph viewer built in SPEC-001 walks history from `HEAD` only
(matching the default `git log`), so any commits that live solely on other
branches — unmerged feature branches, tags pointing at side histories, work in
progress on a branch that is not checked out — are invisible in the graph. This
is a known limitation: SPEC-001 explicitly deferred the "all-branches" view to
a later spec (see its `future_work` learning).

A developer inspecting a repository visually usually wants to see the *whole*
topology — how every branch diverged and (if at all) rejoined — not just the
slice reachable from the current checkout. Without this, the tool can't answer
"what branches exist and how do they relate?", which is the primary reason to
look at a graph rather than a linear log.

This spec extends the git-reading layer to walk from **all refs** (branches —
local *and* remote-tracking — tags, and `HEAD`) instead of `HEAD` alone, so the
existing lane and rendering layers display the full branch/merge structure. It
reuses the SPEC-001 lane algorithm, API shape, and frontend renderer unchanged
wherever possible. The app never fetches (read-only), so remote-tracking
branches only appear when they have already been fetched into `refs/remotes/*`.

## Acceptance criteria

<!-- Numbered, testable criteria. Each describes an observable outcome, not an implementation step. -->

1. When the app is run in all-refs mode against a repository that has commits
   on branches not reachable from `HEAD`, the `/api/commits` response and the
   rendered graph include those commits — commits reachable only from a
   non-checked-out local branch appear in the graph.
2. Commits reachable from tags (annotated or lightweight) that point at
   otherwise-unreachable history are included in all-refs mode. Annotated tags
   are peeled to the commit they ultimately reference.
3. In all-refs mode the set and ordering of returned commits (before the AC-6
   cap is applied) equals the default order of the equivalent all-ref `git log`
   invocation on the golden fixture repos — reverse-chronological by committer
   date (Git's default; this does NOT itself guarantee parent-before-child
   ordering — see Research), verified by asserting equality against that exact
   invocation (`git log --branches --remotes --tags`). No `--topo-order`.
4. Two branches that diverged from a common ancestor and were never merged are
   rendered in distinct lanes, each terminating at its own branch tip, with no
   fabricated merge edge between them.
5. A repository with multiple disconnected root commits (independent
   histories, e.g. an orphan branch) renders every root's history; each
   independent history occupies its own lane(s) and no edge is drawn between
   unrelated histories.
6. The server-side commit cap (default 500) still applies in all-refs mode: the
   endpoint returns at most the configured maximum, selecting the most recent
   commits across all refs, and parents that fall outside the capped window are
   emitted as boundary edges (not dangling references), exactly as in HEAD-only
   mode.
7. The ref-walking mode is selectable at startup (config/argument/env var,
   consistent with SPEC-001's startup configuration) with a documented default;
   HEAD-only behavior from SPEC-001 remains available and unchanged when
   selected.
8. Pointing the app at a path that is not a git repository (or does not exist)
   still returns the clear, user-visible error from SPEC-001 (no crash, no
   blank page) in all-refs mode.
9. The README documents the new mode: how to enable/disable all-refs, what it
   shows, and the default; the documented steps succeed on a clean checkout.
10. In all-refs mode, commits reachable only from remote-tracking branches
    (`refs/remotes/*`, e.g. after a `git fetch`) are included in the
    `/api/commits` response and the rendered graph. The app itself never
    fetches — it only reads refs already present in the repository
    (read-only NFR unchanged).

## Research

Scope note: this extends SPEC-001 (the only `done` spec). Prior learnings come
from `.spec/_ledger/{git-reader,architecture}.yaml` and SPEC-001's `meta.yaml`.

- **This is the exact extension SPEC-001 deferred.** SPEC-001's `future_work`
  learning explicitly names "push all refs into the pygit2 walker / `git log
  --all`" as the follow-up. The core change is ref enumeration + tip dedup +
  multi-tip seeding in `app/git_reader.py`; ref *decoration* (labels) is a
  separate later spec. (learnings-curator)
- **The lane algorithm and frontend need no change for the common cases.**
  `app/graph.py` (lines 66–75) already claims a fresh lane via `_claim_lane`
  for any in-window tip not reserved by a child, which is exactly what unmerged
  branch tips and additional roots require; roots clear their lane and emit no
  edges; boundary edges (`parent not in in_window`) already handle the cap.
  Keep the SPEC-001 "server computes layout, frontend is a dumb renderer"
  split. (repo-analyst, learnings-curator)
- **AC-5 (disconnected histories) is satisfied by construction, but must be
  test-guarded.** Edges are only ever created from a commit's real `parents`
  (`_edge` in `app/graph.py`), so no fabricated edge can appear between
  unrelated histories. This matters because Git's own `graph.c` had a 2026 bug
  where multiple parentless roots *rendered as if related* (visual column
  stacking, not real edges); our row-per-commit SVG avoids the visual variant,
  but a test asserting "no cross-history edge and each root on its own lane"
  should lock this in. (prior-art-researcher)
- **Ordering correction (changes AC-3 wording): Git's default order does NOT
  guarantee parent-before-child.** Only `--date-order`, `--author-date-order`,
  and `--topo-order` document that guarantee; plain `git log` is just reverse
  chronological by committer time. `pygit2` `SortMode.TIME` matches that plain
  default (SPEC-001's choice, ledger-confirmed). The greedy lane algorithm
  *implicitly assumes* children are processed before parents; with strictly
  increasing commit timestamps (true for our fixtures and the overwhelming
  common case) this holds, but rebased branches with equal/inverted timestamps
  can violate it. Decision: keep `SortMode.TIME` for AC-3 parity with `git log`
  (consistency with SPEC-001) and add a fixture that would expose lane
  misbehavior; treat a switch to `SortMode.TOPOLOGICAL | SortMode.TIME`
  (= `--date-order`) as an out-of-scope fallback if a real correctness failure
  surfaces. (docs-researcher, prior-art-researcher, learnings-curator)
- **pygit2 multi-tip API is confirmed.** `walker = repo.walk(None,
  pygit2.enums.SortMode.TIME)` then `walker.push(oid)` per tip is valid
  (libgit2 requires at least one push before walking). Enumerate via
  `repo.references.iterator(...)` / `repo.branches.local`; resolve symbolic
  refs (`HEAD`) with `.resolve()` before reading `.target`; **peel annotated
  tags** with `Reference.peel(pygit2.Commit)` (lightweight tags' `.target` is
  already a commit). Skip refs that don't peel to a commit (tag-of-tree/blob →
  `InvalidSpecError`/`GIT_EPEEL`) and dedupe tips by OID. Use
  `pygit2.enums.SortMode` (the `GIT_SORT_*` constants are removed in pygit2
  1.20). (docs-researcher)
- **Ref scope = branches (local + remote-tracking) + tags; use
  `--branches --remotes --tags` (+ HEAD).** The subprocess fallback and the
  golden oracle use `git log --branches --remotes --tags`; the pygit2 path
  enumerates `refs/heads/*`, `refs/remotes/*`, and `refs/tags/*`. (Scope note:
  remotes were pulled in after the initial local-only implementation — see the
  `scope_changed` learning.) The app never fetches, so remote-tracking refs
  only appear if already present. The cap (`--max-count`) applies to the single
  merged, ordered stream — the newest N across all refs, not per-branch — so a
  branch with only old commits can fall entirely outside the window; that is
  truncation, not an unmerged tip, and tests must not conflate the two.
  (docs-researcher, prior-art-researcher)
- **Fixture-building hazard.** New fixtures (unmerged branch, tag-on-side-
  history, orphan/disconnected root) need deterministic dates. Per SPEC-001's
  hard-won learning (promoted to `.cursor/rules/shell-env-hygiene.mdc`), set
  `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE` per-subprocess (as `tests/conftest.py`
  `RepoBuilder` already does), never in the shared shell. Extend `RepoBuilder`
  with `tag(name, annotated=)` and `orphan(branch)` helpers. `branched_repo`
  is a poor all-refs discriminator (its feature branch is merged, so HEAD-only
  and all-refs return the same 6 commits) — a genuinely *unmerged* fixture is
  required for AC-1/AC-4. (repo-analyst, learnings-curator)

## Scope boundaries

Explicitly OUT of scope for this spec (candidates for later specs):

- **Ref decoration / labels** — drawing branch, tag, and `HEAD` name labels on
  or next to nodes. This spec only makes the commits *visible*; naming which
  ref points where is a separate spec.
- Per-branch show/hide toggles or an interactive ref selector in the UI — mode
  is fixed at startup, matching SPEC-001's no-runtime-config boundary.
- Commit detail view, diffs, search/filtering, in-UI repo picker (still later
  specs, per SPEC-001).
- Any change to the lane-assignment algorithm's core strategy beyond what is
  required to seed it from multiple tips; writing to the repository (read-only
  remains a hard NFR).

## User scenarios

- **Surveying all active branches:** A developer opens a repo with several
  in-flight feature branches that were never merged and immediately sees each
  branch as its own colored lane diverging from the main line, understanding
  the repo's overall topology at a glance.
- **Auditing an orphan/disconnected history:** A developer who created an
  orphan branch (e.g. a `gh-pages`-style separate history) can see that history
  rendered alongside the main one, confirming the two share no commits.

## Non-functional requirements

- Read-only: the app must never mutate the target repository (unchanged from
  SPEC-001).
- Responsiveness: `/api/commits` still returns within ~1s for a repo of a few
  thousand commits when capped; walking multiple refs must not regress this
  materially (the walk is still O(commits) up to the cap).
- Cross-platform: continues to run on Windows, macOS, and Linux; the ref
  enumeration must use the same cross-platform library path as SPEC-001
  (`pygit2` primary, `git` subprocess fallback).
- Determinism: lane/color assignment must remain deterministic given the same
  ref set and cap, so acceptance tests are stable.

## Implementation guidance

This builds directly on the SPEC-001 modules. Keep the change localized to the
reader and its configuration; the lane algorithm (`app/graph.py`) and frontend
(`web/`) should need little or no change because they already consume an
ordered commit list and render whatever tips appear in-window.

- **Files likely affected:**
  - `app/git_reader.py` — extend `read_commits` with a ref-mode parameter
    (e.g. `all_refs: bool = False`) threaded into both backends; **default
    `False` keeps HEAD-only behavior byte-for-byte**. `pygit2`: create
    `walker = repo.walk(None, pygit2.enums.SortMode.TIME)` and `walker.push(oid)`
    for each resolved tip. Enumerate every ref under `refs/heads/*`,
    `refs/remotes/*`, and `refs/tags/*`, plus `HEAD`; **peel** each with
    `Reference.peel(pygit2.Commit)` (lightweight tags/branches are already
    commits; annotated tags peel through); skip refs that don't peel to a
    commit (e.g. tag-of-tree/blob, dangling `refs/remotes/origin/HEAD`);
    dedupe tips by OID; if no pushable tips remain, return `[]`. Keep the
    empty/unborn-HEAD guard unchanged. `git log` fallback: use
    `git log --branches --remotes --tags` with the same `--max-count`/`--pretty`.
    Preserve the HEAD-only path and `CommitRecord`/`RepositoryError` semantics
    unchanged.
  - `app/config.py` — add a startup setting for ref mode (e.g. `--all-refs`
    flag or `--refs {head,all}`) with an env-var equivalent, following the
    existing `Settings`/`parse_args` pattern and `DEFAULT_*` constants.
  - `app/server.py` — pass the ref-mode setting through to `read_commits`. API
    response shape is unchanged (optionally surface the active mode in the JSON
    metadata alongside `repo`/`max_commits`).
  - `web/` — no rendering change expected; verify multi-root / multi-tip graphs
    draw correctly (they already do via `lane_count` + per-commit lanes). Only
    touch if a real rendering bug surfaces with multiple independent tips.
  - `README.md` — document the new mode, its default, and the toggle (AC-9).
  - `tests/conftest.py` — add fixtures: an unmerged-branch repo (branch tip not
    reachable from HEAD), a tags-pointing-at-side-history repo, a
    disconnected/orphan-history repo, and a remote-tracking-branch repo (a
    fetched `refs/remotes/*` tip not reachable from any local ref, for AC-10).
  - `tests/test_git_reader.py`, `tests/test_graph.py`, `tests/test_api.py` —
    add all-refs cases; keep existing HEAD-only assertions intact.
- **Files NOT to modify:** anything under `.cursor/` and `.spec/` (Creator
  scaffolding); do not modify or write to the *target* git repository
  (read-only NFR); do not change SPEC-001's HEAD-only semantics or its existing
  passing tests — add alongside them.
- **Patterns to follow:**
  - Mirror SPEC-001's dual-backend reader structure: implement all-refs for
    both the `pygit2` path and the `git log` subprocess fallback, and keep the
    subprocess path as the ordering oracle for the AC-3 equality test (now
    `git log --branches --remotes --tags`).
  - Reuse `CommitRecord` and `build_graph` unchanged; the greedy lane algorithm
    already claims a fresh lane for any in-window tip not reserved by a child,
    which is exactly what unmerged branch tips and extra roots need.
  - Keep ref mode a startup-only setting (no request-time parameter), matching
    the SPEC-001 no-runtime-repo-config boundary.
- **Test expectations:**
  - Reader: an unmerged branch's commits appear in all-refs output but NOT in
    HEAD-only output (AC-1); tag-only history appears and annotated tags are
    peeled (AC-2); all-refs order equals `git log --branches --remotes --tags`
    on a branched fixture (AC-3); a remote-tracking-only commit appears in
    all-refs but not HEAD-only (AC-10); cap still limits count and picks newest
    across refs (AC-6).
  - Graph: two unmerged branches occupy distinct lanes with no spurious merge
    edge (AC-4); disconnected roots each render on their own lane with NO edge
    whose endpoint is in an unrelated history (AC-5 — assert edges only ever
    reference real parents); boundary edges appear for parents beyond the cap in
    all-refs mode (AC-6). Add a fixture with equal/near-equal commit timestamps
    across branches to sanity-check lane assignment does not depend on a
    parent-before-child guarantee the default order does not provide (see
    Research).
  - API: `/api/commits` in all-refs mode returns the extra commits and the
    documented fields (AC-1/AC-7-equivalent); bad-repo path still returns the
    clear 400 error (AC-8).
  - README steps verified on a clean virtual environment (AC-9).
