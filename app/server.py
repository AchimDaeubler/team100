"""FastAPI application: serves the commit-graph JSON API and the static frontend.

The repository path is fixed at startup via :mod:`app.config`. The app never
writes to the target repository.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, parse_args
from app.git_reader import RepositoryError, read_commits
from app.graph import build_graph

WEB_DIR = Path(__file__).resolve().parent.parent / "web"


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Commit Graph Viewer", version="0.1.0")
    app.state.settings = settings

    @app.get("/api/commits")
    def get_commits() -> JSONResponse:
        try:
            commits = read_commits(settings.repo_path, settings.max_commits)
        except RepositoryError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        graph = build_graph(commits)
        return JSONResponse(
            {
                "repo": settings.repo_path,
                "max_commits": settings.max_commits,
                "count": len(graph["commits"]),
                "lane_count": graph["lane_count"],
                "commits": graph["commits"],
            }
        )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")
    return app


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    settings = parse_args(argv)
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
