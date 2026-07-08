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
- Newest-first ordering matching the default `git log`.
- Optional **all-refs mode** to walk every branch (local and remote-tracking)
  and tag (not just `HEAD`), so unmerged branches, remote branches, and side
  histories are visible.
- Server-side commit cap (default 500) so it stays responsive on large repos.
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
      ]
    }
  ]
}
```

Pointing at a path that is not a git repository returns `400` with
`{ "error": "…" }` instead of crashing.

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
— local and remote-tracking — and tags) and renders them. Out of scope for now:
commit detail/diff view, branch/tag/HEAD ref decoration (drawing ref name labels
on nodes), an in-UI repo picker or per-branch toggles, search/filtering, and
pagination beyond the fixed cap.
