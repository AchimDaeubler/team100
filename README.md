# Commit Graph Viewer

A lightweight, read-only web app that reads a **local** git repository and
renders its commit history as a visual graph — commit nodes connected by
branch/merge lines, in separate colored lanes — similar to the graph pane in
GitLab/GitHub.

It never writes to the target repository.

## Features

- Reads commits from a local repo via [`pygit2`](https://www.pygit2.org/)
  (no `git` binary required), with a `git log` subprocess fallback.
- Renders a commit graph in the browser as SVG: nodes, branch/merge edges, and
  parallel development in separate colored lanes.
- **Ref decoration:** each commit that a ref points directly at shows a labeled
  badge — local branches, remote-tracking branches, tags, and a `HEAD → …`
  indicator — right next to its node, matching `git log --decorate` semantics.
- Newest-first ordering matching the default `git log`.
- Optional **all-refs mode** to walk every branch (local and remote-tracking)
  and tag (not just `HEAD`), so unmerged branches, remote branches, and side
  histories are visible.
- Server-side commit cap (default 500) so it stays responsive on large repos.
- **Click a commit to open a detail panel** with the full message, author &
  committer identities/timestamps, parent SHAs, and the list of files changed.
- Clear error message when pointed at a path that is not a git repository.

## Requirements

- Python 3.11+
- A local git repository to point it at

`git` is optional (only used by the fallback reader); `pygit2` ships prebuilt
wheels for Windows, macOS, and Linux.

## Install

From the project root, in a clean virtual environment:

```bash
# Linux / macOS
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```powershell
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run

Point the app at a repository (defaults to the current directory):

```bash
python -m app.server /path/to/your/repo
```

```powershell
python -m app.server C:\path\to\your\repo
```

Then open <http://127.0.0.1:8000> in your browser.

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `repo_path` (positional) | `.` or `$REPO_PATH` | Path to the local git repository |
| `--max-commits` | `500` | Maximum commits returned (applied server-side) |
| `--all-refs` | *off* (HEAD-only) | Walk all branches (local + remote-tracking) and tags, not just `HEAD` |
| `--host` | `127.0.0.1` | Bind host |
| `--port` | `8000` | Bind port |

Each option also has an environment-variable equivalent: `REPO_PATH`,
`MAX_COMMITS`, `ALL_REFS`, `HOST`, `PORT`.

### Viewing all branches (all-refs mode)

By default the viewer walks history from `HEAD` only, exactly like `git log`, so
commits that live solely on other branches (unmerged feature branches, tags
pointing at side histories, orphan/disconnected histories) are not shown.

Pass `--all-refs` to instead seed the walk from **every branch — local and
remote-tracking — every tag, and `HEAD`** — equivalent to
`git log --branches --remotes --tags`. Annotated tags are peeled to the commit
they reference. Remote branches appear once they have been fetched (the app is
read-only and never fetches for you); run `git fetch` yourself first if you want
the latest remote refs reflected.

```bash
python -m app.server /path/to/your/repo --all-refs
```

```powershell
# Windows (PowerShell) — flag or environment variable
python -m app.server C:\path\to\your\repo --all-refs
$env:ALL_REFS = "1"; python -m app.server C:\path\to\your\repo
```

The commit cap (`--max-commits`) still applies to the merged stream: you get the
most recent commits across all refs, and parents that fall outside that window
are drawn as boundary edges. The default remains HEAD-only, so existing behavior
is unchanged unless you opt in.

> **Security note:** the app binds to `127.0.0.1` (localhost) by default and has
> no authentication. It is a single-user local tool. If you change `--host` to a
> non-loopback address (e.g. `0.0.0.0`), the repository's commit metadata
> (messages, author names/emails, the server-side repo path) becomes reachable
> unauthenticated on your network. Only do this on a trusted network.

## API

`GET /api/commits` returns JSON:

```jsonc
{
  "repo": "/path/to/repo",
  "max_commits": 500,
  "refs": "head",          // "head" (default) or "all" when --all-refs is set
  "count": 6,
  "lane_count": 2,
  "commits": [
    {
      "sha": "…40 hex…",
      "short_sha": "21b5ce8",
      "parents": ["…", "…"],
      "subject": "Merge feature into main",
      "author_name": "Demo User",
      "author_email": "demo@example.com",
      "authored_timestamp": 1767272400,
      "lane": 0,
      "color": "#0072B2",
      "edges": [
        { "parent": "…", "to_lane": 0, "color": "#0072B2", "boundary": false }
      ],
      "refs": [
        { "name": "main",        "type": "branch", "is_head": true  },
        { "name": "origin/main", "type": "remote", "is_head": false },
        { "name": "v1.0",        "type": "tag",    "is_head": false }
      ]
    }
  ]
}
```

Pointing at a path that is not a git repository returns `400` with
`{ "error": "…" }` instead of crashing.

**Per-commit `refs` array** *(one entry per ref that points directly at the
commit; empty when no ref does, matching `git log --decorate` semantics)*:

| Field     | Type     | Meaning                                                                 |
|-----------|----------|-------------------------------------------------------------------------|
| `name`    | string   | Short ref name (`main`, `origin/main`, `v1.0` — never `refs/heads/…`).  |
| `type`    | string   | One of `branch` (local), `remote` (remote-tracking), `tag`, `head`.     |
| `is_head` | boolean  | `true` for the entry that HEAD currently points at.                     |

- Annotated tags decorate the commit they ultimately peel to (not the tag
  object itself). `refs/remotes/*/HEAD` symbolic aliases are excluded.
- When HEAD is **attached** to a branch, the matching branch entry carries
  `is_head: true` so the UI renders `HEAD → main`. When HEAD is **detached**,
  a dedicated entry `{ "name": "HEAD", "type": "head", "is_head": true }` is
  attached to the commit HEAD points at.
- Refs whose tip commit falls outside the returned window (truncated by the
  `--max-commits` cap or unreachable in the current walk mode) simply do not
  appear — no dangling entries. Decoration is computed regardless of walk
  mode, so `HEAD` and its branch label are visible even in the default
  HEAD-only mode.
- Note the naming overlap: the **top-level `refs`** field is the walk-mode
  string (`"head"` / `"all"`); the **per-commit `refs`** field is this
  decoration array. Same key name, different nesting.

### `GET /api/commits/{sha}`

Returns full detail for a single commit. `{sha}` may be a full 40-hex SHA or a
short prefix of at least 4 hex characters; input case is accepted in any mix
and normalized to lowercase before lookup (matching `git rev-parse`).

```jsonc
{
  "sha": "…40 hex…",
  "short_sha": "21b5ce8",
  "parents": ["…", "…"],          // full SHAs; ≥2 entries for a merge commit
  "subject": "Merge feature into main",
  "message": "Merge feature into main\n\nFull body, line breaks preserved.",
  "author_name": "Demo User",
  "author_email": "demo@example.com",
  "authored_timestamp": 1767272400,
  "committer_name": "Demo User",
  "committer_email": "demo@example.com",
  "committer_timestamp": 1767272400,
  "files": [
    { "path": "src/app.py", "change_kind": "M" },
    { "path": "docs/new.md", "change_kind": "A" },
    { "path": "lib/new.py", "change_kind": "R", "old_path": "lib/old.py" }
  ],
  "files_truncated": false,
  "total_files": 3
}
```

- `change_kind` is a single letter: `A` added, `M` modified, `D` deleted,
  `R` renamed, `C` copied (`T`/others may also appear, e.g. submodule changes).
  `old_path` is present only for renames/copies.
- **File-list cap:** the `files` array is capped at **200** entries. When a
  commit changes more files, `files_truncated` is `true` and `total_files`
  reports the real count; the UI shows a trailing "… and N more" line.
- **Initial commit** (no parents): every path is diffed against the empty tree
  and appears as `A`.
- **Merge commit** (2+ parents): the file list is the diff against the **first
  parent** (the "what did this merge bring in" convention used by
  GitHub/GitLab, not `git show`'s combined-diff default); the UI labels it
  `vs <short-sha of first parent>`.

Status codes:

| Status | When | Body |
|--------|------|------|
| `200` | Commit found | detail object above |
| `400` | Malformed SHA (not 4–40 hex), ambiguous short prefix, or unreadable repo | `{ "error": "…" }` |
| `404` | Well-formed SHA that does not exist in the repository | `{ "error": "…" }` |

Fetching commit detail is strictly read-only — no refs, objects, working tree,
or index are modified.

## Ref decoration (branch, tag & HEAD badges)

Each commit that a ref points **directly** at (its tip) is decorated with one
or more badges rendered next to its node in the graph. This makes it easy to
answer questions like "which lane is `main`?", "where's `HEAD` right now?", or
"where does `v1.0` point?" — the labels are the same short names you see with
`git log --decorate`.

Four badge types, distinguished by both color and a leading glyph (so the
distinction does not rely on color alone):

| Type       | Glyph | Meaning                                                                    |
|------------|:-----:|----------------------------------------------------------------------------|
| **branch** | `⎇`   | Local branch (`refs/heads/*`). Example: `main`, `feature/login`.           |
| **remote** | `☁`   | Remote-tracking branch (`refs/remotes/*`). Example: `origin/main`. Dashed border. |
| **tag**    | `⚑`   | Tag (`refs/tags/*`). Annotated tags peel to their target commit.            |
| **HEAD**   | `◉`   | The current HEAD. Rendered with a thicker, emphasized border.               |

**`HEAD → branch` indicator.** When HEAD is attached to a branch, the row's
HEAD/branch badge is rendered as a single combined label (`HEAD → main`) with
the emphasized HEAD styling. When HEAD is **detached** (checkout of a specific
commit or tag), a standalone emphasized `HEAD` badge appears on the commit
HEAD points at, alongside any other refs (tags, branches) that also decorate
that commit.

**Multiple refs on one commit.** A single commit can carry any number of
badges — for example a release commit that is simultaneously the tip of
`main`, `origin/main`, and `v1.0`. Badges appear in a stable order: HEAD
first, then local branches, then remote-tracking branches, then tags. Very
long ref names are truncated with an ellipsis; hover a badge to reveal the
full ref name in a tooltip.

Decoration is **display-only**: badges are labels, not controls, and clicking
one falls through to open the commit detail panel just as clicking anywhere
else on the row does.

## Commit detail panel

Click any commit node or its row to open a detail panel (a modal dialog docked
to the right). It shows the full SHA, the complete commit message, author and
committer identities and timestamps, the parent short-SHAs (clickable when the
parent is in the current graph window), and the list of changed files (capped
at 200, with a "… and N more" indicator beyond that).

Keyboard: `Tab` moves between commit rows; `Enter`/`Space` opens the panel and
moves focus into it; `Esc` (or the Close button, or clicking outside) closes it
and returns focus to the row you opened. Opening the panel does not reflow the
graph.

## Development

Run the test suite (builds small golden fixture repositories and checks the
reader, lane algorithm, and API):

```bash
pip install -r requirements-dev.txt
pytest
```

## Project layout

```
app/
  config.py       # startup configuration (repo path, cap, host/port)
  git_reader.py   # read commits from a local repo (pygit2 + git log fallback)
  graph.py        # greedy lane-assignment algorithm + colors + boundary edges
  server.py       # FastAPI app: /api/commits + static frontend
web/
  index.html      # page shell
  app.js          # SVG graph renderer
  styles.css      # styling
tests/            # pytest suite + golden fixture repositories
```

## Scope

This slice reads commits (from `HEAD` or, with `--all-refs`, from all branches
— local and remote-tracking — and tags), renders them as a graph with
per-commit ref badges (branches, tags, and a `HEAD → …` indicator), and lets
you click any commit for a detail panel (metadata + changed-file list).
Rendering the actual diff/patch content is a separate later spec. Also out of
scope for now: in-UI toggles to filter refs (hide tags, focus a branch),
clicking a badge to check out/navigate, ref decoration inside the detail
panel, an in-UI repo picker, search/filtering, and pagination beyond the
fixed cap.
