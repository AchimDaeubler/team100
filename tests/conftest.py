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

    def commit(self, message: str, advance: int = 3600) -> str:
        # ``advance=0`` reuses the current clock so sibling commits can share a
        # timestamp (exercises lane assignment without a parent-before-child
        # ordering guarantee — see the spec Research note).
        self._clock += advance
        # Empty commits keep the DAG shape without file bookkeeping.
        self._git("commit", "-q", "--allow-empty", "-m", message)
        return self._git("rev-parse", "HEAD").strip()

    def checkout(self, branch: str, create: bool = False) -> None:
        if create:
            self._git("checkout", "-q", "-b", branch)
        else:
            self._git("checkout", "-q", branch)

    def orphan(self, branch: str) -> None:
        """Start a new disconnected history (root will have no parent)."""
        # Empty commits mean no tracked files, so the new branch starts clean.
        self._git("checkout", "-q", "--orphan", branch)

    def delete_branch(self, branch: str) -> None:
        self._git("branch", "-q", "-D", branch)

    def tag(self, name: str, annotated: bool = False, message: str | None = None) -> None:
        if annotated:
            self._git("tag", "-a", name, "-m", message or name)
        else:
            self._git("tag", name)

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
def unmerged_repo(tmp_path: Path) -> Path:
    """main plus a feature branch that was never merged back.

    HEAD (main) reaches only the 3 main commits; the 2 feature commits are
    reachable solely via the unmerged branch tip (AC-1, AC-4).
    """
    b = RepoBuilder(tmp_path / "unmerged")
    b.commit("Main: first")
    b.commit("Main: second")
    b.checkout("feature", create=True)
    b.commit("Feature: work a")
    b.commit("Feature: work b")
    b.checkout("main")
    b.commit("Main: third")
    return b.path


@pytest.fixture
def tagged_side_history_repo(tmp_path: Path) -> Path:
    """A side history reachable only through tags (AC-2).

    The ``side`` branch is deleted after tagging, so its commits are reachable
    only via an annotated tag (peeled to a commit) and a lightweight tag.
    """
    b = RepoBuilder(tmp_path / "tagged")
    b.commit("Main: first")
    b.checkout("side", create=True)
    b.commit("Side: one")
    b.tag("light-side", annotated=False)  # lightweight tag → target is a commit
    b.commit("Side: two")
    b.tag("v1-side", annotated=True, message="annotated side tag")  # peels to commit
    b.checkout("main")
    b.delete_branch("side")  # side commits now reachable only via the two tags
    b.commit("Main: second")
    return b.path


@pytest.fixture
def orphan_repo(tmp_path: Path) -> Path:
    """Two disconnected histories: main and an orphan branch (AC-5)."""
    b = RepoBuilder(tmp_path / "orphan")
    b.commit("Main: first")
    b.commit("Main: second")
    b.orphan("independent")
    b.commit("Orphan: first")
    b.commit("Orphan: second")
    b.checkout("main")
    return b.path


@pytest.fixture
def remote_tracking_repo(tmp_path: Path) -> Path:
    """A repo with a remote-tracking branch whose commits are not on any local
    ref (AC-10).

    An ``upstream`` repo gains a ``remote-feature`` branch with unique commits;
    the working repo adds it as a remote and fetches, so those commits live only
    under ``refs/remotes/up/*`` — invisible HEAD-only, visible in all-refs mode.
    """
    upstream = RepoBuilder(tmp_path / "upstream")
    upstream.commit("Upstream: base")
    upstream.checkout("remote-feature", create=True)
    upstream.commit("Remote: only-a")
    upstream.commit("Remote: only-b")
    upstream.checkout("main")

    downstream = RepoBuilder(tmp_path / "downstream")
    # Offset the clock so downstream commit times don't collide with upstream's.
    downstream._clock = 1_000_000
    downstream.commit("Local: first")
    downstream._git("remote", "add", "up", str(upstream.path))
    downstream._git("fetch", "-q", "up")
    return downstream.path


@pytest.fixture
def equal_timestamp_repo(tmp_path: Path) -> Path:
    """Two unmerged tips sharing an identical commit timestamp (AC-4).

    Both branch tips are committed at the same clock value, so the default
    time-ordered walk cannot rely on a parent-before-child guarantee between
    them — a sanity check for the greedy lane algorithm.
    """
    b = RepoBuilder(tmp_path / "equal_ts")
    b.commit("base")  # older root, on main
    b.checkout("branch-a", create=True)
    b.commit("a tip")  # clock = base + 3600
    b.checkout("main")
    b.checkout("branch-b", create=True)
    b.commit("b tip", advance=0)  # same clock as 'a tip'
    b.checkout("main")
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
