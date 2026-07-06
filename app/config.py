"""Runtime configuration for the commit-graph viewer.

The target repository path and the server-side commit cap are provided at
startup (CLI argument or environment variable), never at request time — the
repo picker is explicitly out of scope for this spec.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

DEFAULT_MAX_COMMITS = 500
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


@dataclass(frozen=True)
class Settings:
    repo_path: str
    max_commits: int = DEFAULT_MAX_COMMITS
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT


def parse_args(argv: list[str] | None = None) -> Settings:
    parser = argparse.ArgumentParser(
        prog="commit-graph-viewer",
        description="Read a local git repository and serve its commit graph.",
    )
    parser.add_argument(
        "repo_path",
        nargs="?",
        default=os.environ.get("REPO_PATH", "."),
        help="Path to the local git repository (default: $REPO_PATH or current dir).",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=int(os.environ.get("MAX_COMMITS", DEFAULT_MAX_COMMITS)),
        help=f"Max commits returned (default: {DEFAULT_MAX_COMMITS}).",
    )
    parser.add_argument("--host", default=os.environ.get("HOST", DEFAULT_HOST))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", DEFAULT_PORT)))
    ns = parser.parse_args(argv)
    return Settings(
        repo_path=ns.repo_path,
        max_commits=max(1, ns.max_commits),
        host=ns.host,
        port=ns.port,
    )
