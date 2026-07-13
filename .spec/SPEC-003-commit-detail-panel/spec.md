---
id: SPEC-003
title: "Commit detail panel (click to inspect a commit)"
category: feature
owner: achim.daeubler                     # git config user.name
authored_by: augmented                # augmented | automated
---

## Problem statement

The commit-graph viewer (SPEC-001) currently shows one dense row per commit —
short SHA, subject, author, date — with a hover tooltip repeating the same
fields. To actually inspect a commit (read the full message, see its parents,
check which files it touched) the user has to leave the app and run
`git show` in a terminal.

This spec adds the first-level inspection layer: click a commit → a detail
panel opens with richer metadata (full message, both author and committer
identities/timestamps, parent SHAs, and the list of files changed). It is the
foundation for the later diff-view spec, which will render actual patch content
into this panel. The graph remains the primary surface; the panel is a
non-destructive addition to it.

## Acceptance criteria

<!-- Numbered, testable criteria. Each describes an observable outcome, not an implementation step. -->

1. Clicking a commit node OR its row area opens a detail panel bound to that
   commit; clicking a Close control, clicking outside the panel, or pressing
   Escape closes it.
2. The panel shows, for the selected commit: full 40-hex SHA (monospaced), the
   **full** commit message (subject + body, preserving line breaks), author
   name & email, committer name & email, authored timestamp, committer
   timestamp, and the list of parent SHAs (each shown as the 7-char short SHA
   and linking/selecting that commit when clicked, if it is in the current
   graph window).
3. The panel shows the list of files changed in the commit, each with its
   repo-relative path and a change-kind letter (`A` added, `M` modified,
   `D` deleted, `R` renamed, `C` copied). The list is capped at 200 files by
   default; when the commit exceeds the cap a trailing "… and N more" line
   indicates the omission.
4. For the initial commit (no parents), the file list is populated by
   diffing against the empty tree — every path in the commit tree appears as
   `A` — rather than being empty or throwing.
5. For a merge commit (2+ parents), the file list defaults to the diff against
   the **first parent** (matching the GitHub/GitLab web convention of "what
   this merge brought in from the branch"; explicitly not `git show`'s CLI
   default of `--cc` dense-combined diff) and the panel labels the diff as
   `vs <short-sha of first parent>`.
6. The backend exposes `GET /api/commits/{sha}` that returns JSON containing:
   `sha`, `short_sha`, `parents` (list of full SHAs), `subject`, `message`
   (full), `author_name`, `author_email`, `authored_timestamp`,
   `committer_name`, `committer_email`, `committer_timestamp`, `files`
   (list of `{path, change_kind, old_path?}` where `old_path` is present only
   for renames/copies), `files_truncated` (bool), and `total_files` (int).
7. `GET /api/commits/{sha}` returns HTTP `404` with `{"error": "..."}` when
   the SHA is well-formed but does not exist in the repository, HTTP `400`
   with `{"error": "..."}` when the SHA is malformed (not 4–40 hex
   characters, case-insensitive), and HTTP `400` with `{"error": "..."}`
   when a short-SHA prefix is ambiguous (matches multiple objects). Full
   SHAs and short-SHA prefixes of at least 4 characters both resolve;
   input case is accepted in any mix (`Abc1234` = `abc1234`) and
   normalized to lowercase before lookup, matching `git rev-parse` semantics.
8. Fetching commit detail performs no writes: no repository refs are updated,
   no objects are added, no working tree or index files change. This is
   verified by a test that snapshots `.git/` before and after the fetch and
   asserts equality.
9. Opening the panel does not reflow the existing graph — the SVG stays
   scrollable and the previously-selected row remains visible when the panel
   is open. The selected row is visually highlighted while the panel is open.
10. Accessibility: the panel is exposed as a modal dialog (`role="dialog"` +
    `aria-modal="true"` + `aria-labelledby` on a visible title, or the
    native `<dialog>` element with `.showModal()`). Focusing a commit row
    and pressing Enter or Space opens the panel and moves focus into it;
    Escape closes the panel and restores focus to the row that opened it;
    Tab / Shift+Tab cycle within the panel while it is open.
11. `README.md` documents the click-to-open behavior, the file-list cap, and
    the new `/api/commits/{sha}` endpoint (fields, status codes).

## Research

- **Extend, don't reshape, SPEC-001's dual-backend reader.** `app/git_reader.py`
  already establishes pygit2-primary + `git` CLI-fallback with a
  `RepositoryError` mapped to HTTP 400 in `app/server.py`. The new
  `read_commit_detail` should follow the same shape (frozen dataclass,
  `to_dict()`, `_FIELD_SEP` NUL parsing in the CLI branch). Ledger entry
  `.spec/_ledger/git-reader.yaml` documents this as the canonical pattern.
  (repo-analyst, learnings-curator)
- **Compute detail server-side; frontend stays a dumb renderer.** The ledger
  `.spec/_ledger/architecture.yaml` (promoted from SPEC-001) prescribes that
  testable, deterministic derivations live on the server. Merge-vs-first-parent
  selection, empty-tree diff for the root commit, and the 200-file cap
  therefore belong in `read_commit_detail`, not the drawer. (learnings-curator)
- **Route new endpoint before the static `/` mount; no route collision.**
  `app/server.py` mounts `StaticFiles(html=True)` at `/`. FastAPI matches
  registered routes before mounts, and `/api/commits/{sha}` is more specific
  than the existing `/api/commits`, so ordering is only a stylistic concern —
  keep the new route adjacent to the existing one for readability.
  (repo-analyst, docs-researcher)
- **Use `JSONResponse` for 404/400, not `HTTPException`.** The existing
  `/api/commits` returns `JSONResponse(status_code=400, content={"error":
  "..."})`. `HTTPException(detail=...)` would emit `{"detail": ...}` and break
  the envelope contract. Preserve `JSONResponse` for the new error paths so
  the client can rely on a single error shape. (docs-researcher, repo-analyst)
- **Path-param validation uses `pattern=`, not the deprecated `regex=`.**
  FastAPI 0.100+ (repo pins `>=0.115`) accepts the SHA regex as
  `Annotated[str, Path(pattern=r"^[0-9a-fA-F]{4,40}$")]`. Any-case hex is
  accepted per Git's `rev-parse` semantics; normalize to lowercase inside the
  reader before object lookup so downstream comparisons and cache keys stay
  consistent (matches SPEC-001 lowercase-hex convention).
  (docs-researcher, prior-art-researcher)
- **pygit2 lookup exception mapping is a hard contract.** `repo[sha]` raises
  `KeyError` on `GIT_ENOTFOUND` (well-formed SHA missing) and `ValueError` on
  `GIT_EAMBIGUOUS` (short prefix matches multiple objects). Both must be
  caught explicitly in `read_commit_detail` **before** the broad
  `except Exception` that triggers the CLI fallback — otherwise a missing SHA
  would silently retry via `git show` and mask itself as a 400 instead of
  404. Introduce `UnknownCommitError(RepositoryError)` in `app/git_reader.py`
  and map it to 404 in `app/server.py`; keep the base class → 400.
  (docs-researcher, repo-analyst)
- **pygit2 diff idioms.** For a normal commit,
  `repo.diff(commit.parents[0], commit)` (per pygit2's own git-show recipe) or
  the tree-level equivalent `commit.parents[0].tree.diff_to_tree(commit.tree)`
  give "changes introduced by commit". For the initial (parentless) commit,
  the documented empty-tree idiom is `commit.tree.diff_to_tree(swap=True)` —
  no need to construct an empty tree manually. Iterate `diff.deltas` (faster
  than `Patch` objects) and read `delta.status_char()`, `delta.new_file.path`,
  `delta.old_file.path`. Rename/copy detection is opt-in: call
  `diff.find_similar()` **before** iterating deltas, or `R`/`C` deltas will
  appear as `D`+`A` pairs. pygit2 defaults (50% similarity threshold, 1000
  rename limit) match Git's own defaults. (docs-researcher, prior-art-researcher)
- **CLI fallback tokenization for `git show --name-status -z`.** Combining a
  custom `--pretty=format:%H%x00%P%x00%an%x00%ae%x00%at%x00%cn%x00%ce%x00%ct%x00%B`
  with `-s --name-status -z` in a single `git show` invocation yields:
  (1) the metadata block with NUL-separated fields terminated by an extra
  NUL (because the format contains `%`, Git treats it as `tformat:` and
  appends a terminator — a NUL under `-z`), then (2) NUL-delimited
  name-status records where renames/copies expand to three tokens
  (`R100\0old\0new\0`, score glued to the status letter with no separator).
  Parse the metadata block up to the tformat terminator, then consume
  name-status records to EOF. (docs-researcher)
- **First-parent merge diff is a UI convention, not the CLI default.** Plain
  `git show <merge>` defaults to `--cc` (dense-combined) — hunks that differ
  from *all* parents. The GitHub/GitLab web convention is a first-parent
  diff, because that answers "what did this merge bring in?" This spec
  matches the web convention (AC-5), and the panel label
  `vs <short-sha of first parent>` makes the choice explicit to the user —
  something CLI viewers rarely do. Selectors for other parents are deferred
  to a later spec. (prior-art-researcher)
- **Root commit → diff against the empty tree; carries no known crash risk if
  guarded.** The empty-tree diff renders as "all files added". Real footguns
  are (a) calling `commit.parents[0]` unconditionally (fatal on root), and
  (b) hardcoding the SHA-1 empty-tree hash `4b825dc...` — libgit2/pygit2
  handles the SHA object model internally, so the `swap=True` idiom above is
  the safe path. (docs-researcher, prior-art-researcher)
- **AC-8 read-only test needs `GIT_OPTIONAL_LOCKS=0` on the CLI subprocess.**
  Otherwise `git show` may take `.git/index.lock` for an optional index
  refresh, which is a real source of intermittent snapshot failures in
  read-only viewer test suites (e.g. GitHub Desktop). Set the env var in the
  subprocess call (not the shell — per `.cursor/rules/shell-env-hygiene.mdc`).
  Verify with a `.git/` snapshot before/after that compares directory
  contents (skipping any transient lock files). pygit2 read paths (`repo[oid]`,
  `repo.diff`, `Tree.diff_to_tree`) don't require this. (prior-art-researcher,
  learnings-curator)
- **File cap of 200 is well-positioned; keep the visible truncation
  indicator.** GitLab collapses at 100, GitHub hard-caps at 3,000; 200 fits a
  local viewer's latency target (~300 ms) and matches typical commit sizes
  (median <10 files). `files_truncated: true` + `total_files: N` + a
  "…and N more" line in the panel matches GitLab's transparency model.
  (prior-art-researcher)
- **Panel accessibility = modal dialog, not a live region.** WAI-ARIA APG's
  Dialog (Modal) pattern is the authoritative match for a click-opened
  overlay that closes on Escape: `role="dialog"` + `aria-modal="true"` +
  `aria-labelledby`, focus moves in on open and restores to the trigger on
  close, Tab cycles inside. The native `<dialog>` element with
  `.showModal()` provides all of this without a JS focus-trap library.
  `aria-live` is only a supplementary announcement, not a substitute.
  (docs-researcher, prior-art-researcher)
- **Parent short-SHA links use SPEC-001's boundary-edge convention.** In the
  SPEC-001 renderer, parents outside the fetched window are already
  represented as dashed boundary edges (not clickable). The detail panel
  should follow the same convention: a parent short-SHA is a link only when
  the parent SHA is in the current `rowOf` map; otherwise render as inert
  text. (learnings-curator, repo-analyst)
- **Golden fixtures need extension.** `tests/conftest.py` uses
  `--allow-empty` throughout, so no fixture produces file diffs today. The
  spec needs new `RepoBuilder` helpers (or new fixtures) with real file
  content, at least one `git mv` rename, and a merge commit with divergent
  file changes on both sides — otherwise ACs 3/4/5 have no meaningful
  coverage. (repo-analyst, prior-art-researcher)
- **Byte-string hygiene for non-UTF-8 commits.** Git commit objects are byte
  strings; commit messages and author names occasionally contain non-UTF-8
  bytes (Latin-1 legacy, malformed sequences). Decode with
  `errors='replace'` (or `surrogateescape` if we want lossless round-trip)
  in both backends. pygit2 attributes are already `str` — trust them; the
  CLI path uses `text=True, encoding='utf-8'` today and needs the errors
  handler added. (prior-art-researcher)
- **Submodule entries and binary files are non-blocking edge cases.**
  Submodule (`160000` mode) changes appear as `T` in `--name-status`; treat
  them as path-only entries in the file list, no special icon for now.
  Binary files show up in the list as `A`/`M`/`D` with no diff distinction
  needed at this scope — the actual patch content is deferred to the
  later diff-view spec. (prior-art-researcher)

## Scope boundaries

<!-- What is explicitly out of scope. -->

- **Rendering the actual diff / patch content** — the panel shows only the
  file list here. The unified/side-by-side diff view is a separate later
  spec that builds on this endpoint.
- Ref decoration on graph nodes or in the panel (branch/tag/HEAD labels) —
  separate later spec.
- Extending the walk to all local/remote branches — separate later spec.
- Search or filtering of commits — separate later spec.
- Pagination beyond SPEC-001's `--max-commits` cap — separate later spec.
- In-UI repo picker — separate later spec.
- Copy-to-clipboard buttons, external links (e.g. "open on GitHub"), GPG
  signature verification indicators.
- Writing to the target repository in any form (hard NFR carried from
  SPEC-001).

## User scenarios

- **Reviewer inspects a merge commit before approving:** on the graph, clicks
  the merge node, reads the full commit message, notes both parent SHAs, and
  scans the file list to confirm the merge only touched the expected areas.
- **Author checks their own recent commit:** clicks a commit they just made
  to verify the subject/body wrapped correctly, sees the file list, and
  closes the panel without leaving the browser.
- **Keyboard-only navigation:** tabs through commit rows, presses Enter on
  one, reads the announced detail, closes with Escape, continues tabbing.

## Non-functional requirements

- **Read-only.** Fetching commit detail must not mutate the target
  repository (refs, objects, working tree, index). This is enforced by test
  and is a hard NFR carried from SPEC-001.
- **Latency.** `GET /api/commits/{sha}` returns within ~300 ms for a typical
  commit (≤200 files changed) on a moderate repository, measured locally.
- **Cross-platform.** Same Windows/macOS/Linux support as SPEC-001. Works
  under both the pygit2 backend and the `git`-CLI subprocess fallback.
- **Backward compatibility.** The existing `GET /api/commits` response shape
  is unchanged. The new endpoint is additive.

## Implementation guidance

<!-- (Recommended) File paths to modify, patterns to follow, test expectations.
     Use repo-root-relative paths for repo files, and describe local-only artifacts
     generically instead of pasting machine-specific paths like `/home/...` or `/Users/...`. -->

- **Files likely affected:**
  - `app/git_reader.py` — add:
    - `UnknownCommitError(RepositoryError)` immediately after
      `RepositoryError` (subclass so the base `except RepositoryError:
      raise` branch still re-raises without triggering CLI fallback).
    - `@dataclass(frozen=True) FileChange(path: str, change_kind: str,
      old_path: str | None = None)` with `to_dict()`.
    - `@dataclass(frozen=True) CommitDetail(...)` with the full AC-6 field
      set (`sha`, `short_sha`, `parents`, `subject`, `message`,
      `author_name`, `author_email`, `authored_timestamp`, `committer_name`,
      `committer_email`, `committer_timestamp`, `files`, `files_truncated`,
      `total_files`) and `to_dict()`.
    - `read_commit_detail(repo_path: str, sha: str, max_files: int = 200)
      -> CommitDetail` — normalize `sha` to lowercase, clamp `max_files`
      to ≥1 (matching `read_commits`), try pygit2 primary, fall back to
      git CLI on non-`RepositoryError` exceptions, catching `KeyError`/
      `ValueError` from pygit2 lookup explicitly as
      `UnknownCommitError` / `RepositoryError` (ambiguous prefix) *before*
      the broad handler.
    - `_read_commit_detail_pygit2`: `repo[sha]` for lookup; for a normal
      commit use `repo.diff(commit.parents[0], commit)`; for a root commit
      use `commit.tree.diff_to_tree(swap=True)`; call `diff.find_similar()`
      before iterating; walk `diff.deltas` reading `delta.status_char()`,
      `delta.new_file.path`, `delta.old_file.path` (only populate
      `old_path` when it differs from `new_path`, i.e. for `R`/`C`); count
      total, truncate to `max_files`, set `files_truncated`.
    - `_read_commit_detail_git`: single `git show -s --name-status -z
      --pretty=format:%H%x00%P%x00%an%x00%ae%x00%at%x00%cn%x00%ce%x00%ct%x00%B`
      invocation via `subprocess.run` with `env={**os.environ,
      "GIT_OPTIONAL_LOCKS": "0"}` (env scoped to this subprocess only, per
      `.cursor/rules/shell-env-hygiene.mdc`), `text=True, encoding='utf-8',
      errors='replace'`. Parse the metadata block up to the tformat
      terminator NUL, then consume NUL-terminated name-status records
      (three tokens for `R`/`C`, two for others). Map `git`'s exit status
      to `UnknownCommitError` when stderr indicates "bad revision" /
      unknown object.
  - `app/server.py` — new route:
    ```python
    from typing import Annotated
    from fastapi import Path
    @app.get("/api/commits/{sha}")
    def get_commit_detail(sha: Annotated[str, Path(pattern=r"^[0-9a-fA-F]{4,40}$")]) -> JSONResponse:
        try:
            detail = read_commit_detail(settings.repo_path, sha)
        except UnknownCommitError as exc:
            return JSONResponse(status_code=404, content={"error": str(exc)})
        except RepositoryError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        return JSONResponse(detail.to_dict())
    ```
    Register this route in `create_app` before the `StaticFiles` mount
    (matching current ordering). Note: `Path(pattern=…)` failures yield
    422 (FastAPI validation), not the `{"error": ...}` 400 envelope — add
    a small validation-exception handler that rewrites 422s on this route
    to the project envelope, or catch the format error manually in the
    route body if the envelope contract is strict.
  - `web/index.html` — add `<aside id="detail" hidden role="dialog"
    aria-modal="true" aria-labelledby="detail-title">…</aside>` (or a
    `<dialog id="detail">` element) as a sibling of `#graph`, containing a
    header (`<h2 id="detail-title">Commit</h2>`), a Close button
    (`aria-label="Close commit detail"`), and empty containers the JS
    populates.
  - `web/app.js` —
    - attach click handlers to existing `row-hit` rects and `.node`
      circles (single delegated listener on the SVG root is cleanest);
    - fetch `/api/commits/{sha}`, populate the drawer;
    - manage `.row-hit.selected` (and `.node.selected`) highlight;
    - keyboard: Enter/Space on a focused row (rows need `tabindex="0"`)
      opens; Escape closes; simple focus-trap while open; restore focus
      to the trigger row on close;
    - if using `<dialog>.showModal()`, focus trap and Escape-close are
      built in;
    - render parent short-SHAs as clickable only when `rowOf.has(parent)`
      (SPEC-001 boundary-edge convention).
  - `web/styles.css` — style `#detail` as a fixed-position right drawer
    (`position: fixed; right: 0; top: <header-height>; bottom: 0; width:
    420px; z-index: 3;`) using the existing dark palette variables
    (`--panel`, `--border`, `--fg`, `--muted`). Add `.row-hit.selected`
    highlight distinct from `:hover`. The drawer overlays the graph — the
    SVG width and scroll behavior must not change.
  - `tests/conftest.py` — extend `RepoBuilder` (or add sibling helpers)
    to write real file content, add a `mv` helper for renames, and
    provide a fixture `content_repo` with: root commit adding files,
    modify commit, delete commit, rename commit, and a merge commit whose
    two parents each modify different files (so first-parent diff has
    non-empty content). Add a `many_files_repo` fixture with >200 files
    in one commit for truncation coverage.
  - `tests/test_git_reader.py` — parametrize over both backends (pygit2
    and CLI) where `git` is available; cover: root commit → all `A`;
    simple modify → `M`; delete → `D`; rename detected → `R` with
    `old_path` set and `!= new_path`; merge → first-parent semantics;
    `max_files` truncation → `files_truncated=True` with correct
    `total_files`; unknown SHA raises `UnknownCommitError`; ambiguous
    prefix (if pygit2 exposes) raises `RepositoryError`; SHA case
    normalization (`ABC1234` == `abc1234`); `.git/` directory snapshot
    equality before/after (per AC-8).
  - `tests/test_api.py` — `TestClient(create_app(Settings(repo_path=…)))`
    tests covering: 200 with the full AC-6 field set for a known SHA;
    404 for a well-formed unknown SHA; 400 for a malformed SHA (envelope
    is `{"error": ...}`); short-SHA prefix resolution (7-hex prefix);
    merge-commit label (`vs <short-sha>`); mixed-case SHA input; existing
    `/api/commits` response shape unchanged (regression guard).
  - `README.md` — extend the "API" section with `/api/commits/{sha}` (all
    AC-6 fields, 200/400/404 status codes with the `{"error": ...}`
    envelope), and add a short "Commit detail" section describing the
    click-to-open behavior, keyboard shortcuts, and the 200-file cap.
- **Files NOT to modify:**
  - `app/graph.py` — the lane algorithm is orthogonal; leaving it
    untouched preserves SPEC-001's regression baseline.
  - `app/config.py` — no new startup config surface (the 200-file cap is
    a function default, not a CLI/env option).
  - `app/__init__.py` — version-only file.
  - `requirements.txt` / `requirements-dev.txt` — current pins already
    cover everything (`fastapi[standard]>=0.115` for `Path`/`TestClient`,
    `pygit2>=1.19` for `Repository.diff` / `Diff.find_similar` /
    `DiffDelta.status_char`).
  - Anything under `.cursor/` or `.spec/` outside this spec directory.
  - The **target** git repository (hard read-only NFR carried from
    SPEC-001).
- **Patterns to follow:**
  - Dual-backend try/except from `read_commits`; both backends emit the
    same `CommitDetail` shape so tests can parametrize.
  - Frozen dataclass + `to_dict()` (SPEC-001 `CommitRecord` precedent).
  - `_FIELD_SEP = "\x00"` and `%x00` NUL-joined pretty format for the CLI
    branch; matches the existing `_read_git_log` parser.
  - `RepositoryError`/`UnknownCommitError` domain errors → `JSONResponse`
    envelope in `server.py`; never leak exceptions to the response body.
  - `Path(pattern=r"^[0-9a-fA-F]{4,40}$")` — do not use the deprecated
    `regex=` kwarg (removed idiom in FastAPI 0.100+ / Pydantic v2).
  - Scope subprocess env vars via the `env=` argument to `subprocess.run`
    (`GIT_OPTIONAL_LOCKS=0`), never via the shared shell — per
    `.cursor/rules/shell-env-hygiene.mdc`.
  - Preserve SPEC-001's boundary-edge convention for parents outside the
    fetched graph window (dashed edges → non-clickable panel entries).
- **Test expectations:**
  - `.git/` snapshot equality (recursive directory hash or file-list
    comparison, ignoring transient lock files) around every detail-read
    code path proves AC-8.
  - The CLI-fallback path is exercised in tests (parametrization or an
    explicit test that patches out pygit2), matching SPEC-001's dual-path
    coverage discipline — the reader currently has no explicit fallback
    test and this spec should close that gap for its own new code.
  - At least one end-to-end API test hits `TestClient.get(
    "/api/commits/{sha}")` against a real fixture repo (not a mock) to
    exercise the full route → reader → response chain.
  - Regression test: `GET /api/commits` (list) response shape is
    unchanged — SPEC-001's contract must stay intact.
