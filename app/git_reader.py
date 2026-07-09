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

import os
import shutil
import subprocess
from dataclasses import asdict, dataclass


class RepositoryError(Exception):
    """Raised when the target path is not a readable git repository (AC-8)."""


class UnknownCommitError(RepositoryError):
    """Raised when a well-formed SHA does not resolve to a commit.

    Subclasses :class:`RepositoryError` so the dual-backend dispatch re-raises
    it (instead of falling back to the git CLI) while :mod:`app.server` can map
    it to HTTP 404 rather than the base class's 400.
    """


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


@dataclass(frozen=True)
class FileChange:
    path: str
    change_kind: str  # A/M/D/R/C/T… (git --name-status status char)
    old_path: str | None = None  # populated only for renames/copies

    def to_dict(self) -> dict:
        d: dict = {"path": self.path, "change_kind": self.change_kind}
        if self.old_path is not None:
            d["old_path"] = self.old_path
        return d


@dataclass(frozen=True)
class CommitDetail:
    sha: str
    short_sha: str
    parents: list[str]
    subject: str
    message: str  # full message (subject + body), line breaks preserved.
    author_name: str
    author_email: str
    authored_timestamp: int
    committer_name: str
    committer_email: str
    committer_timestamp: int
    files: list[FileChange]
    files_truncated: bool
    total_files: int

    def to_dict(self) -> dict:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "parents": list(self.parents),
            "subject": self.subject,
            "message": self.message,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "authored_timestamp": self.authored_timestamp,
            "committer_name": self.committer_name,
            "committer_email": self.committer_email,
            "committer_timestamp": self.committer_timestamp,
            "files": [f.to_dict() for f in self.files],
            "files_truncated": self.files_truncated,
            "total_files": self.total_files,
        }


def read_commit_detail(
    repo_path: str, sha: str, max_files: int = 200
) -> CommitDetail:
    """Return full detail for a single commit resolved from ``sha``.

    ``sha`` may be a full 40-hex SHA or a short prefix (>=4 hex); it is
    normalized to lowercase before lookup (matching ``git rev-parse``). Raises
    :class:`UnknownCommitError` when the SHA is well-formed but missing, and
    :class:`RepositoryError` for an unreadable repo or an ambiguous prefix.
    """
    sha = sha.strip().lower()
    if max_files < 1:
        max_files = 1
    try:
        return _read_commit_detail_pygit2(repo_path, sha, max_files)
    except RepositoryError:
        raise
    except Exception as exc:  # pygit2 unavailable/failed → try git CLI fallback.
        if shutil.which("git"):
            return _read_commit_detail_git(repo_path, sha, max_files)
        raise RepositoryError(
            f"Could not read git repository at {repo_path!r}: {exc}"
        ) from exc


def _read_commit_detail_pygit2(
    repo_path: str, sha: str, max_files: int
) -> CommitDetail:
    import pygit2

    discovered = pygit2.discover_repository(repo_path)
    if discovered is None:
        raise RepositoryError(
            f"{repo_path!r} is not a git repository (or does not exist)."
        )
    repo = pygit2.Repository(discovered)

    try:
        obj = repo[sha]  # accepts full oid or a hex prefix.
    except KeyError as exc:
        raise UnknownCommitError(
            f"No commit found for {sha!r}."
        ) from exc
    except ValueError as exc:
        raise RepositoryError(
            f"Ambiguous commit prefix {sha!r} (matches multiple objects)."
        ) from exc

    try:
        commit = obj.peel(pygit2.Commit)
    except Exception as exc:
        raise UnknownCommitError(f"{sha!r} does not refer to a commit.") from exc

    if commit.parents:
        diff = repo.diff(commit.parents[0], commit)
    else:
        diff = commit.tree.diff_to_tree(swap=True)
    diff.find_similar()  # opt-in rename/copy detection (git defaults).

    files: list[FileChange] = []
    total = 0
    for delta in diff.deltas:
        total += 1
        if len(files) < max_files:
            kind = delta.status_char()
            new_path = delta.new_file.path
            old_path = delta.old_file.path
            path = new_path or old_path
            old = old_path if kind in ("R", "C") else None
            files.append(FileChange(path=path, change_kind=kind, old_path=old))

    full_sha = str(commit.id)
    message = commit.message.rstrip("\n")
    return CommitDetail(
        sha=full_sha,
        short_sha=full_sha[:7],
        parents=[str(pid) for pid in commit.parent_ids],
        subject=_subject(commit.message),
        message=message,
        author_name=commit.author.name,
        author_email=commit.author.email,
        authored_timestamp=int(commit.author.time),
        committer_name=commit.committer.name,
        committer_email=commit.committer.email,
        committer_timestamp=int(commit.committer.time),
        files=files,
        files_truncated=total > max_files,
        total_files=total,
    )


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


def _classify_commit_error(repo_path: str, stderr: str) -> RepositoryError:
    """Map a failed ``git`` invocation to the right domain error.

    Ambiguous prefixes and unreadable repos become :class:`RepositoryError`
    (HTTP 400); a well-formed-but-missing revision becomes
    :class:`UnknownCommitError` (HTTP 404).
    """
    low = stderr.lower()
    if "ambiguous" in low and "unknown revision" not in low:
        return RepositoryError(
            f"Ambiguous commit prefix (matches multiple objects): {stderr}"
        )
    missing_markers = (
        "unknown revision",
        "bad revision",
        "bad object",
        "not a valid object",
        "no such",
    )
    if any(marker in low for marker in missing_markers):
        return UnknownCommitError(f"No commit found: {stderr}")
    return RepositoryError(
        f"{repo_path!r} is not a git repository (or does not exist): {stderr}"
    )


def _read_commit_detail_git(
    repo_path: str, sha: str, max_files: int
) -> CommitDetail:
    # Scope GIT_OPTIONAL_LOCKS to this subprocess only (never the shared shell,
    # per .cursor/rules/shell-env-hygiene.mdc) so a read cannot grab
    # .git/index.lock and mutate the repo (AC-8).
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    # Use git's literal ``%x00`` escape rather than embedding real NUL bytes in
    # the argument: git expands ``%x00`` to NUL in its *output*, while the
    # argument string stays NUL-free (Windows CreateProcess rejects an embedded
    # null character in argv). The output is still split on ``_FIELD_SEP``.
    fmt = "%x00".join(
        ["%H", "%P", "%an", "%ae", "%at", "%cn", "%ce", "%ct", "%B"]
    )

    def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["git", "-C", repo_path, *args],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
        except OSError as exc:  # noqa: BLE001 - re-raised as domain error
            raise RepositoryError(
                f"Failed to run git at {repo_path!r}: {exc}"
            ) from exc

    meta = _run(["show", "-s", f"--pretty=format:{fmt}", sha])
    if meta.returncode != 0:
        raise _classify_commit_error(repo_path, (meta.stderr or "").strip())

    parts = meta.stdout.split(_FIELD_SEP)
    if len(parts) < 9:
        raise RepositoryError(
            f"Unexpected git output for commit {sha!r}."
        )
    full_sha, parents_raw, an, ae, at_, cn, ce, ct = parts[:8]
    message = _FIELD_SEP.join(parts[8:]).rstrip("\n")
    parents = parents_raw.split() if parents_raw else []

    # Diff the FIRST parent's tree against the commit (mirrors pygit2's
    # ``repo.diff(commit.parents[0], commit)``) so merges show the first-parent
    # diff (AC-5); ``git diff-tree <merge>`` alone emits nothing for merges.
    # The root commit (no parents) uses ``--root`` -> empty-tree diff (AC-4).
    diff_args = ["diff-tree", "--no-commit-id", "--name-status", "-z", "-r", "-M", "-C"]
    if parents:
        diff_args += [parents[0], full_sha]
    else:
        diff_args += ["--root", full_sha]
    changed = _run(diff_args)
    if changed.returncode != 0:
        raise _classify_commit_error(repo_path, (changed.stderr or "").strip())

    tokens = [t for t in changed.stdout.split(_FIELD_SEP) if t]
    files: list[FileChange] = []
    total = 0
    i = 0
    while i < len(tokens):
        status = tokens[i]
        kind = status[0]
        i += 1
        if kind in ("R", "C"):
            old_path = tokens[i] if i < len(tokens) else ""
            new_path = tokens[i + 1] if i + 1 < len(tokens) else old_path
            i += 2
            path, old = new_path, old_path
        else:
            path = tokens[i] if i < len(tokens) else ""
            i += 1
            old = None
        total += 1
        if len(files) < max_files:
            files.append(FileChange(path=path, change_kind=kind, old_path=old))

    return CommitDetail(
        sha=full_sha,
        short_sha=full_sha[:7],
        parents=parents,
        subject=_subject(message),
        message=message,
        author_name=an,
        author_email=ae,
        authored_timestamp=int(at_),
        committer_name=cn,
        committer_email=ce,
        committer_timestamp=int(ct),
        files=files,
        files_truncated=total > max_files,
        total_files=total,
    )
