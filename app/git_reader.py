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
from dataclasses import asdict, dataclass, field, replace


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
    # SPEC-004: ref decoration. Each entry is {"name": str, "type": one of
    # "branch"|"remote"|"tag"|"head", "is_head": bool}. Empty for commits that
    # no ref points at directly (tip-only semantics, matching `git log
    # --decorate`). Populated by ``read_commits`` from a repo-wide tip→refs
    # map — decoration is orthogonal to the walk mode, so refs are attached
    # even in HEAD-only mode; refs whose tip commit falls outside the
    # returned window simply do not appear on any record.
    refs: list[dict] = field(default_factory=list)

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
        records = _read_pygit2(repo_path, max_commits, all_refs)
        decoration = _decoration_pygit2(repo_path)
    except RepositoryError:
        raise
    except Exception as exc:  # pygit2 unavailable/failed → try git CLI fallback.
        if shutil.which("git"):
            records = _read_git_log(repo_path, max_commits, all_refs)
            decoration = _decoration_git(repo_path)
        else:
            raise RepositoryError(
                f"Could not read git repository at {repo_path!r}: {exc}"
            ) from exc
    return _attach_refs(records, decoration)


def _attach_refs(
    records: list[CommitRecord], decoration: dict[str, list[dict]]
) -> list[CommitRecord]:
    """Return copies of ``records`` with each ``refs`` populated from the map.

    ``decoration`` maps full-SHA to a list of ref entries. Commits absent from
    the map (i.e. no ref points at them directly) keep an empty ``refs`` list,
    which is the AC-1 shape. This is where the boundary rule from AC-7 is
    enforced: refs whose tip commit is not in ``records`` simply do not
    surface — we only assign entries to records we return.
    """
    if not decoration:
        return records
    attached: list[CommitRecord] = []
    for rec in records:
        refs = decoration.get(rec.sha)
        if refs:
            attached.append(replace(rec, refs=list(refs)))
        else:
            attached.append(rec)
    return attached


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


_REF_TYPE_BY_PREFIX = (
    ("refs/heads/", "branch"),
    ("refs/remotes/", "remote"),
    ("refs/tags/", "tag"),
)


def _decoration_pygit2(repo_path: str) -> dict[str, list[dict]]:
    """Build a full-SHA → list[ref-entry] map via the pygit2 backend.

    Enumerates local branches, remote-tracking branches, and tags. Each ref is
    peeled to its ultimate commit — annotated tags via
    ``Reference.peel(pygit2.Commit)`` handle tag-of-tag recursively; refs that
    peel to a tree/blob or dangle are silently skipped (the ``_tip_oids``
    peel/skip idiom). ``refs/remotes/*/HEAD`` symbolic aliases are excluded
    because they name a branch, not a commit tip. HEAD is resolved separately:
    attached HEAD marks the matching local-branch entry ``is_head=True`` so
    the UI can render ``HEAD → main``; detached HEAD gets a dedicated
    ``{name:"HEAD", type:"head", is_head:True}`` entry on the pointed-at
    commit (AC-4).
    """
    import pygit2

    discovered = pygit2.discover_repository(repo_path)
    if discovered is None:
        raise RepositoryError(
            f"{repo_path!r} is not a git repository (or does not exist)."
        )
    repo = pygit2.Repository(discovered)
    if repo.head_is_unborn or repo.is_empty:
        return {}

    symbolic_type = getattr(pygit2.enums, "ReferenceType", None)
    symbolic_value = getattr(symbolic_type, "SYMBOLIC", None) if symbolic_type else None

    decoration: dict[str, list[dict]] = {}

    for name in repo.references:
        ref_type: str | None = None
        for prefix, kind in _REF_TYPE_BY_PREFIX:
            if name.startswith(prefix):
                ref_type = kind
                break
        if ref_type is None:
            continue
        ref = repo.references[name]
        # Skip refs/remotes/<remote>/HEAD-style symbolic aliases: they name a
        # branch by another name, not a distinct tip. Guard by type when the
        # enum is available, and belt-and-braces on the name suffix.
        if symbolic_value is not None and ref.type == symbolic_value:
            continue
        if name.endswith("/HEAD") and ref_type == "remote":
            continue
        try:
            commit = ref.peel(pygit2.Commit)
        except Exception:
            # Tag-of-tree/blob, dangling ref, or otherwise non-commit target.
            continue
        entry = {"name": ref.shorthand, "type": ref_type, "is_head": False}
        decoration.setdefault(str(commit.id), []).append(entry)

    # HEAD: attached → mark the matching local-branch entry; detached → add a
    # dedicated head entry on the pointed-at commit.
    if repo.head_is_detached:
        try:
            head_commit_id = str(repo.head.peel(pygit2.Commit).id)
            decoration.setdefault(head_commit_id, []).append(
                {"name": "HEAD", "type": "head", "is_head": True}
            )
        except Exception:
            pass
    else:
        try:
            branch_name = repo.head.shorthand
            head_commit_id = str(repo.head.peel(pygit2.Commit).id)
            for entry in decoration.get(head_commit_id, []):
                if entry["type"] == "branch" and entry["name"] == branch_name:
                    entry["is_head"] = True
                    break
        except Exception:
            pass

    return decoration


def _decoration_git(repo_path: str) -> dict[str, list[dict]]:
    """Build a full-SHA → list[ref-entry] map via one ``git for-each-ref`` pass.

    Format string emits five NUL-separated fields per ref: object name, short
    ref name, peeled-object name (annotated tag → target commit), object type,
    peeled object type. When ``*objecttype == commit`` we take ``*objectname``
    (annotated tag peeled to a commit); otherwise if ``objecttype == commit``
    we take ``objectname`` (branch, remote-tracking, or lightweight tag on a
    commit). Anything else (tag of tree/blob) is skipped, mirroring the
    pygit2 peel/skip idiom. ``refs/remotes/*/HEAD`` symbolic aliases are
    filtered by name. HEAD is resolved by ``git symbolic-ref -q --short HEAD``
    (attached → branch short name; non-zero exit → detached) plus
    ``git rev-parse HEAD``.

    Uses ``%00`` for the NUL escape — ``for-each-ref``'s own literal — rather
    than a literal NUL in argv (Windows ``CreateProcess`` rejects embedded
    NULs, SPEC-003 gotcha). Note the escape differs by git subcommand:
    ``git log``/``show`` pretty-format uses ``%x00``; ``for-each-ref`` uses
    ``%00``. A real footgun documented in the SPEC-004 research note.
    ``GIT_OPTIONAL_LOCKS`` is scoped via ``env=`` per
    ``.cursor/rules/shell-env-hygiene.mdc``.
    """
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    fmt = "%00".join(
        ["%(objectname)", "%(refname)", "%(*objectname)", "%(objecttype)", "%(*objecttype)"]
    )
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                repo_path,
                "for-each-ref",
                f"--format={fmt}",
                "refs/heads",
                "refs/remotes",
                "refs/tags",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
        )
    except OSError as exc:
        raise RepositoryError(
            f"Failed to run git at {repo_path!r}: {exc}"
        ) from exc
    if proc.returncode != 0:
        # Empty / unborn repos exit 0 with no output; a non-zero exit here
        # means the repo itself is unreadable.
        stderr = (proc.stderr or "").strip()
        raise RepositoryError(
            f"{repo_path!r} is not a git repository (or does not exist): {stderr}"
        )

    decoration: dict[str, list[dict]] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        parts = line.split(_FIELD_SEP)
        if len(parts) < 5:
            continue
        objname, refname, peeled_objname, objtype, peeled_objtype = parts[:5]
        # Determine the ref's namespace + skip symbolic remote-HEAD aliases.
        ref_type: str | None = None
        for prefix, kind in _REF_TYPE_BY_PREFIX:
            if refname.startswith(prefix):
                ref_type = kind
                break
        if ref_type is None:
            continue
        if ref_type == "remote" and refname.endswith("/HEAD"):
            continue

        if peeled_objtype == "commit" and peeled_objname:
            commit_sha = peeled_objname
        elif objtype == "commit":
            commit_sha = objname
        else:
            # Tag of a tree/blob, or a malformed entry — skip (peel/skip).
            continue

        short_name = _short_ref_name(refname)
        decoration.setdefault(commit_sha, []).append(
            {"name": short_name, "type": ref_type, "is_head": False}
        )

    # HEAD resolution — attached vs detached.
    sym = subprocess.run(
        ["git", "-C", repo_path, "symbolic-ref", "-q", "--short", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    head_rev = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    if head_rev.returncode != 0:
        # Unborn HEAD or otherwise no commit yet — no head entry to add.
        return decoration
    head_sha = head_rev.stdout.strip()
    if not head_sha:
        return decoration

    if sym.returncode == 0 and sym.stdout.strip():
        # Attached: mark the matching branch entry as HEAD.
        branch_name = sym.stdout.strip()
        for entry in decoration.get(head_sha, []):
            if entry["type"] == "branch" and entry["name"] == branch_name:
                entry["is_head"] = True
                break
    else:
        # Detached: dedicated HEAD entry on the pointed-at commit.
        decoration.setdefault(head_sha, []).append(
            {"name": "HEAD", "type": "head", "is_head": True}
        )

    return decoration


def _short_ref_name(refname: str) -> str:
    """Strip the canonical ref-namespace prefix.

    ``refs/heads/main`` → ``main``, ``refs/remotes/origin/main`` →
    ``origin/main``, ``refs/tags/v1.0`` → ``v1.0``. Mirrors pygit2's
    ``Reference.shorthand`` so both backends produce the same names.
    """
    for prefix, _kind in _REF_TYPE_BY_PREFIX:
        if refname.startswith(prefix):
            return refname[len(prefix):]
    return refname


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
    # Use git's literal ``%x00`` escape for NUL in the format string rather
    # than embedding a real NUL in argv — Windows ``CreateProcess`` rejects
    # embedded NUL characters (mirrors ``_read_commit_detail_git`` from
    # SPEC-003). Output is still split on ``_FIELD_SEP`` because git expands
    # ``%x00`` to a NUL byte in stdout.
    fmt = "%x00".join(["%H", "%P", "%s", "%an", "%ae", "%at"])
    ref_args = ["--branches", "--remotes", "--tags"] if all_refs else []
    # Scope GIT_OPTIONAL_LOCKS to this subprocess (never the shared shell,
    # per .cursor/rules/shell-env-hygiene.mdc) so the read cannot mutate.
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
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
            env=env,
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
    # A prefix that matches multiple objects yields git's specific
    # "short object ID <x> is ambiguous" (older git: "short SHA1 <x> is
    # ambiguous") line — match the "is ambiguous" phrase, not the bare word
    # "ambiguous". A *missing* revision also prints "ambiguous argument '<x>':
    # unknown revision ...", so keying on "ambiguous" alone would misclassify
    # an unknown SHA as ambiguous (400) instead of not-found (404).
    if "is ambiguous" in low:
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
