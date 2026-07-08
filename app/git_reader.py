"""Read commit history from a local git repository (read-only).

Primary backend is :mod:`pygit2` (libgit2), which needs no ``git`` binary. A
``git log`` subprocess fallback is used when pygit2 cannot open the repo but a
``git`` executable is available; it also serves as the golden reference for
ordering (AC-3).

Ordering matches the default ``git log`` order: reverse chronological by
*committer* date with the parent-before-child guarantee (i.e. ``git log`` with
no extra ordering flags — not ``--topo-order``). The reported timestamp is the
*author* time (AC-2/AC-7). The commit list is capped server-side (AC-9).
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass


class RepositoryError(Exception):
    """Raised when the target path is not a readable git repository (AC-8)."""


@dataclass(frozen=True)
class CommitRecord:
    sha: str
    short_sha: str
    parents: list[str]
    subject: str
    author_name: str
    author_email: str
    authored_timestamp: int  # Unix epoch seconds, author time.

    def to_dict(self) -> dict:
        return asdict(self)


def _subject(message: str) -> str:
    """First line of the commit message, matching git's ``%s``."""
    return message.lstrip("\n").split("\n", 1)[0].strip()


def read_commits(repo_path: str, max_commits: int = 500) -> list[CommitRecord]:
    """Return up to ``max_commits`` commits reachable from HEAD, newest-first.

    Raises :class:`RepositoryError` when ``repo_path`` is missing or is not a
    git repository.
    """
    if max_commits < 1:
        max_commits = 1
    try:
        return _read_pygit2(repo_path, max_commits)
    except RepositoryError:
        raise
    except Exception as exc:  # pygit2 unavailable/failed → try git CLI fallback.
        if shutil.which("git"):
            return _read_git_log(repo_path, max_commits)
        raise RepositoryError(
            f"Could not read git repository at {repo_path!r}: {exc}"
        ) from exc


def _read_pygit2(repo_path: str, max_commits: int) -> list[CommitRecord]:
    import pygit2

    discovered = pygit2.discover_repository(repo_path)
    if discovered is None:
        raise RepositoryError(
            f"{repo_path!r} is not a git repository (or does not exist)."
        )
    repo = pygit2.Repository(discovered)

    if repo.head_is_unborn or repo.is_empty:
        return []

    records: list[CommitRecord] = []
    for commit in repo.walk(repo.head.target, pygit2.enums.SortMode.TIME):
        sha = str(commit.id)
        records.append(
            CommitRecord(
                sha=sha,
                short_sha=sha[:7],
                parents=[str(pid) for pid in commit.parent_ids],
                subject=_subject(commit.message),
                author_name=commit.author.name,
                author_email=commit.author.email,
                authored_timestamp=int(commit.author.time),
            )
        )
        if len(records) >= max_commits:
            break
    return records


_FIELD_SEP = "\x00"


def _read_git_log(repo_path: str, max_commits: int) -> list[CommitRecord]:
    fmt = _FIELD_SEP.join(["%H", "%P", "%s", "%an", "%ae", "%at"])
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "log",
                f"--max-count={max_commits}",
                f"--pretty=format:{fmt}",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError as exc:
        raise RepositoryError(f"Failed to run git at {repo_path!r}: {exc}") from exc

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RepositoryError(
            f"{repo_path!r} is not a git repository (or does not exist): {stderr}"
        )

    records: list[CommitRecord] = []
    for line in proc.stdout.splitlines():
        if not line:
            continue
        sha, parents, subject, name, email, ts = line.split(_FIELD_SEP)
        records.append(
            CommitRecord(
                sha=sha,
                short_sha=sha[:7],
                parents=parents.split() if parents else [],
                subject=subject,
                author_name=name,
                author_email=email,
                authored_timestamp=int(ts),
            )
        )
    return records
