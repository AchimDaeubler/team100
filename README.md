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
| `--host` | `127.0.0.1` | Bind host |
| `--port` | `8000` | Bind port |

Each option also has an environment-variable equivalent: `REPO_PATH`,
`MAX_COMMITS`, `HOST`, `PORT`.

## API

`GET /api/commits` returns JSON:

```jsonc
{
  "repo": "/path/to/repo",
  "max_commits": 500,
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

This is the foundational slice. Out of scope for now: commit detail/diff view,
branch/tag/HEAD ref decoration, an in-UI repo picker, showing all branches
(currently walks from `HEAD` like `git log`), search/filtering, and pagination
beyond the fixed cap.
