"""FastAPI application: serves the commit-graph JSON API and the static frontend.

The repository path is fixed at startup via :mod:`app.config`. The app never
writes to the target repository.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, parse_args
from app.git_reader import (
    RepositoryError,
    UnknownCommitError,
    read_commit_detail,
    read_commits,
)
from app.graph import build_graph

logger = logging.getLogger(__name__)

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

# 4–40 hex chars, any case (git rev-parse semantics); validated in-route so a
# malformed SHA yields the project's {"error": ...} 400 envelope rather than
# FastAPI's default 422 body (AC-7). Matched with re.fullmatch so a trailing
# newline (which "$" would otherwise permit) is rejected.
_SHA_RE = re.compile(r"[0-9a-fA-F]{4,40}")


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title="Commit Graph Viewer", version="0.1.0")
    app.state.settings = settings

    @app.get("/api/commits")
    def get_commits() -> JSONResponse:
        try:
            commits = read_commits(
                settings.repo_path, settings.max_commits, settings.all_refs
            )
        except RepositoryError as exc:
            return JSONResponse(status_code=400, content={"error": str(exc)})
        graph = build_graph(commits)
        return JSONResponse(
            {
                "repo": settings.repo_path,
                "max_commits": settings.max_commits,
                "refs": "all" if settings.all_refs else "head",
                "count": len(graph["commits"]),
                "lane_count": graph["lane_count"],
                "commits": graph["commits"],
            }
        )

    @app.get("/api/commits/{sha}")
    def get_commit_detail(sha: str) -> JSONResponse:
        if not _SHA_RE.fullmatch(sha):
            return JSONResponse(
                status_code=400,
                content={"error": "malformed commit sha"},
            )
        # Domain-error messages can embed the server's repo path or raw git
        # stderr, so log the detail server-side and return a generic client
        # message rather than echoing internals into the response body.
        try:
            detail = read_commit_detail(settings.repo_path, sha)
        except UnknownCommitError as exc:
            logger.info("commit detail not found for %r: %s", sha, exc)
            return JSONResponse(
                status_code=404, content={"error": "commit not found"}
            )
        except RepositoryError as exc:
            logger.warning("commit detail read failed for %r: %s", sha, exc)
            return JSONResponse(
                status_code=400,
                content={"error": "could not read the requested commit"},
            )
        return JSONResponse(detail.to_dict())

    # StaticFiles(html=True) serves web/index.html at "/" and the JS/CSS assets.
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="static")
    return app


def main(argv: list[str] | None = None) -> None:
    import uvicorn

    settings = parse_args(argv)
    app = create_app(settings)
    uvicorn.run(app, host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
