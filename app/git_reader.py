"""Read commit history from a local git repository (read-only).

Primary backend is :mod:`pygit2` (libgit2), which needs no ``git`` binary. A
``git log`` subprocess fallback is used when pygit2 cannot open the repo but a
``git`` executable is available; it also serves as the golden reference for
ordering (AC-3).

Ordering matches the default ``git log`` order: reverse chronological by
*committer* date with the parent-before-child guarantee (i.e. ``git log`` with
no extra ordering flags — not ``--topo-order``). The reported timestamp is the
*author* time (AC-2/AC-7). The commit list is capped server-side (AC-9).

By default the walk starts from ``HEAD`` only (``git log``). When ``all_refs``
is enabled the walk is seeded from every branch (local *and* remote-tracking),
every tag (annotated tags peeled to the commit they reference), and ``HEAD`` —
equivalent to ``git log --branches --remotes --tags``. The app never fetches,
so remote-tracking refs only appear if they were already fetched.
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


def read_commits(
    repo_path: str, max_commits: int = 500, all_refs: bool = False
) -> list[CommitRecord]:
    """Return up to ``max_commits`` commits, newest-first.

    With ``all_refs=False`` (default) the history is walked from ``HEAD`` only,
    matching ``git log`` and preserving SPEC-001 behavior byte-for-byte. With
    ``all_refs=True`` the walk is seeded from all branches (local and
    remote-tracking), tags, and ``HEAD`` (``git log --branches --remotes
    --tags``), so commits that live only on non-checked-out branches, remote
    branches, or side histories are included.

    Raises :class:`RepositoryError` when ``repo_path`` is missing or is not a
    git repository.
    """
    if max_commits < 1:
        max_commits = 1
    try:
        return _read_pygit2(repo_path, max_commits, all_refs)
    except RepositoryError:
        raise
    except Exception as exc:  # pygit2 unavailable/failed → try git CLI fallback.
        if shutil.which("git"):
            return _read_git_log(repo_path, max_commits, all_refs)
        raise RepositoryError(
            f"Could not read git repository at {repo_path!r}: {exc}"
        ) from exc


def _read_pygit2(
    repo_path: str, max_commits: int, all_refs: bool
) -> list[CommitRecord]:
    import pygit2

    discovered = pygit2.discover_repository(repo_path)
    if discovered is None:
        raise RepositoryError(
            f"{repo_path!r} is not a git repository (or does not exist)."
        )
    repo = pygit2.Repository(discovered)

    if repo.head_is_unborn or repo.is_empty:
        return []

    walker = repo.walk(None, pygit2.enums.SortMode.TIME)
    for tip in _tip_oids(repo, pygit2, all_refs):
        walker.push(tip)

    records: list[CommitRecord] = []
    for commit in walker:
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


def _tip_oids(repo, pygit2, all_refs: bool) -> list:
    """OIDs to seed the walk with, deduped, preserving discovery order.

    HEAD-only mode yields just the resolved HEAD commit. All-refs mode adds
    every branch (local ``refs/heads/*`` and remote-tracking
    ``refs/remotes/*``) and every tag; annotated tags are peeled to their
    commit and refs that don't peel to a commit (e.g. a tag of a tree/blob, or
    ``refs/remotes/origin/HEAD`` when it dangles) are skipped.
    """
    seen: set = set()
    tips: list = []

    def add(oid) -> None:
        if oid is not None and oid not in seen:
            seen.add(oid)
            tips.append(oid)

    # HEAD is guaranteed born here (guarded by the caller).
    try:
        add(repo.head.peel(pygit2.Commit).id)
    except Exception:
        pass

    if not all_refs:
        return tips

    ref_prefixes = ("refs/heads/", "refs/remotes/", "refs/tags/")
    for name in repo.references:
        if not name.startswith(ref_prefixes):
            continue
        try:
            commit = repo.references[name].peel(pygit2.Commit)
        except Exception:
            # Non-commit ref (tag of a tree/blob) or a dangling symbolic ref.
            continue
        add(commit.id)

    return tips


_FIELD_SEP = "\x00"


def _read_git_log(
    repo_path: str, max_commits: int, all_refs: bool
) -> list[CommitRecord]:
    fmt = _FIELD_SEP.join(["%H", "%P", "%s", "%an", "%ae", "%at"])
    # --branches --remotes --tags walks every branch (local + remote-tracking)
    # and every tag; omitting them keeps the HEAD-only default.
    ref_args = ["--branches", "--remotes", "--tags"] if all_refs else []
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "log",
                *ref_args,
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
