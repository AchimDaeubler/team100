"""Golden fixture repositories built with the ``git`` CLI.

Each fixture creates a small, deterministic repository (fixed commit dates so
ordering is stable) under a pytest ``tmp_path`` and returns its path. These
exercise the reader and lane algorithm against real git history.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_BASE_EPOCH = 1_700_000_000  # fixed starting point for deterministic dates


class RepoBuilder:
    def __init__(self, path: Path):
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self._clock = 0
        self._git("init", "-q", "-b", "main")
        self._git("config", "user.name", "Test User")
        self._git("config", "user.email", "test@example.com")

    def _git(self, *args: str) -> str:
        # Advance a deterministic clock so committer/author dates strictly increase.
        stamp = f"{_BASE_EPOCH + self._clock} +0000"
        proc = subprocess.run(
            ["git", "-C", str(self.path), *args],
            capture_output=True,
            text=True,
            env=self._env(stamp),
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git {args} failed: {proc.stderr}")
        return proc.stdout

    def _env(self, stamp: str) -> dict:
        import os

        env = os.environ.copy()
        env["GIT_AUTHOR_DATE"] = stamp
        env["GIT_COMMITTER_DATE"] = stamp
        return env

    def commit(self, message: str) -> str:
        self._clock += 3600
        # Empty commits keep the DAG shape without file bookkeeping.
        self._git("commit", "-q", "--allow-empty", "-m", message)
        return self._git("rev-parse", "HEAD").strip()

    def checkout(self, branch: str, create: bool = False) -> None:
        if create:
            self._git("checkout", "-q", "-b", branch)
        else:
            self._git("checkout", "-q", branch)

    def merge(self, *branches: str, message: str) -> str:
        self._clock += 3600
        self._git("merge", "-q", "--no-ff", *branches, "-m", message)
        return self._git("rev-parse", "HEAD").strip()


@pytest.fixture
def empty_repo(tmp_path: Path) -> Path:
    """An initialized repo with no commits (unborn HEAD)."""
    return RepoBuilder(tmp_path / "empty").path


@pytest.fixture
def linear_repo(tmp_path: Path) -> Path:
    b = RepoBuilder(tmp_path / "linear")
    b.commit("first")
    b.commit("second")
    b.commit("third")
    return b.path


@pytest.fixture
def branched_repo(tmp_path: Path) -> Path:
    """main with a feature branch merged back in (one merge commit)."""
    b = RepoBuilder(tmp_path / "branched")
    b.commit("Initial commit")
    b.commit("Main: second")
    b.checkout("feature", create=True)
    b.commit("Feature: add g")
    b.commit("Feature: extend g")
    b.checkout("main")
    b.commit("Main: add h")
    b.merge("feature", message="Merge feature into main")
    return b.path


@pytest.fixture
def octopus_repo(tmp_path: Path) -> Path:
    """An octopus merge joining three branches (3-parent merge commit)."""
    b = RepoBuilder(tmp_path / "octopus")
    b.commit("base")
    b.checkout("b1", create=True)
    b.commit("b1 work")
    b.checkout("main")
    b.checkout("b2", create=True)
    b.commit("b2 work")
    b.checkout("main")
    b.commit("main work")
    b.merge("b1", "b2", message="Octopus merge")
    return b.path
