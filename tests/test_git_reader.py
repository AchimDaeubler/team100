"""Tests for app.git_reader (AC-2, AC-3, AC-7, AC-8, AC-9)."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

import app.git_reader as git_reader
from app.git_reader import (
    RepositoryError,
    UnknownCommitError,
    read_commit_detail,
    read_commits,
)


def _git_log_shas(repo: Path, max_count: int, all_refs: bool = False) -> list[str]:
    ref_args = ["--branches", "--remotes", "--tags"] if all_refs else []
    out = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "log",
            *ref_args,
            f"--max-count={max_count}",
            "--pretty=format:%H",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if line]


def test_reads_fields_and_newest_first(linear_repo: Path):
    commits = read_commits(str(linear_repo))
    assert [c.subject for c in commits] == ["third", "second", "first"]  # AC-3 newest-first
    top = commits[0]
    # AC-2 / AC-7: required fields present and well-formed.
    assert len(top.sha) == 40
    assert top.short_sha == top.sha[:7]
    assert top.author_name == "Test User"
    assert top.author_email == "test@example.com"
    assert isinstance(top.authored_timestamp, int)
    # Root commit has no parents; each later commit has exactly one parent.
    assert commits[-1].parents == []
    assert commits[0].parents == [commits[1].sha]


def test_order_matches_git_log(branched_repo: Path):
    # AC-3: order must equal the default `git log` order on a branched history.
    expected = _git_log_shas(branched_repo, 500)
    actual = [c.sha for c in read_commits(str(branched_repo))]
    assert actual == expected


def test_max_commits_cap_applied_server_side(branched_repo: Path):
    # AC-9: capped to the configured maximum.
    all_commits = read_commits(str(branched_repo), max_commits=500)
    assert len(all_commits) == 6
    capped = read_commits(str(branched_repo), max_commits=2)
    assert len(capped) == 2
    assert [c.sha for c in capped] == [c.sha for c in all_commits[:2]]


def test_merge_commit_has_multiple_parents(branched_repo: Path):
    commits = read_commits(str(branched_repo))
    merge = commits[0]  # newest is the merge commit
    assert merge.subject == "Merge feature into main"
    assert len(merge.parents) == 2  # AC-4


def test_octopus_merge_has_three_parents(octopus_repo: Path):
    merge = read_commits(str(octopus_repo))[0]
    assert len(merge.parents) == 3  # AC-4 stress case


def test_missing_path_raises(tmp_path: Path):
    # AC-8: a nonexistent path is a clear error, not a crash.
    with pytest.raises(RepositoryError):
        read_commits(str(tmp_path / "does_not_exist"))


def test_empty_repo_returns_no_commits(empty_repo: Path):
    # A valid but empty repo (unborn HEAD) is not an error; it has no commits.
    assert read_commits(str(empty_repo)) == []


def test_non_repo_directory_raises(tmp_path: Path):
    # AC-8: an existing directory that is not a git repo errors clearly.
    plain = tmp_path / "plain"
    plain.mkdir()
    with pytest.raises(RepositoryError):
        read_commits(str(plain))


# --- all-refs mode (SPEC-002) ------------------------------------------------


def test_all_refs_includes_unmerged_branch(unmerged_repo: Path):
    # AC-1: commits on an unmerged branch are invisible HEAD-only but present
    # in all-refs mode.
    head_subjects = {c.subject for c in read_commits(str(unmerged_repo))}
    assert "Feature: work b" not in head_subjects
    assert len(head_subjects) == 3

    all_subjects = {c.subject for c in read_commits(str(unmerged_repo), all_refs=True)}
    assert {"Feature: work a", "Feature: work b"} <= all_subjects
    assert len(all_subjects) == 5


def test_head_only_default_unchanged(unmerged_repo: Path):
    # AC-7: default remains HEAD-only, byte-for-byte equal to git log.
    expected = _git_log_shas(unmerged_repo, 500, all_refs=False)
    actual = [c.sha for c in read_commits(str(unmerged_repo))]
    assert actual == expected


def test_all_refs_includes_tag_only_history(tagged_side_history_repo: Path):
    # AC-2: history reachable only via tags (annotated peeled + lightweight) is
    # included; HEAD-only sees just the two main commits.
    head = {c.subject for c in read_commits(str(tagged_side_history_repo))}
    assert head == {"Main: first", "Main: second"}

    all_subjects = {
        c.subject for c in read_commits(str(tagged_side_history_repo), all_refs=True)
    }
    assert {"Side: one", "Side: two"} <= all_subjects


def test_all_refs_order_matches_git_log_all(branched_repo: Path):
    # AC-3: all-refs order equals `git log --branches --tags` exactly. No topo.
    expected = _git_log_shas(branched_repo, 500, all_refs=True)
    actual = [c.sha for c in read_commits(str(branched_repo), all_refs=True)]
    assert actual == expected


def test_all_refs_order_matches_git_log_unmerged(unmerged_repo: Path):
    # AC-3 on a genuinely unmerged history (branched_repo's feature is merged).
    expected = _git_log_shas(unmerged_repo, 500, all_refs=True)
    actual = [c.sha for c in read_commits(str(unmerged_repo), all_refs=True)]
    assert actual == expected


def test_all_refs_cap_picks_newest_across_refs(unmerged_repo: Path):
    # AC-6: the cap limits the merged stream to the newest N across all refs.
    full = read_commits(str(unmerged_repo), max_commits=500, all_refs=True)
    assert len(full) == 5
    capped = read_commits(str(unmerged_repo), max_commits=3, all_refs=True)
    assert len(capped) == 3
    assert [c.sha for c in capped] == [c.sha for c in full[:3]]


def test_all_refs_disconnected_histories_all_present(orphan_repo: Path):
    # AC-5: every root's history is walked in all-refs mode.
    head = {c.subject for c in read_commits(str(orphan_repo))}
    assert head == {"Main: first", "Main: second"}
    all_subjects = {c.subject for c in read_commits(str(orphan_repo), all_refs=True)}
    assert all_subjects == {
        "Main: first",
        "Main: second",
        "Orphan: first",
        "Orphan: second",
    }


def test_all_refs_bad_repo_still_raises(tmp_path: Path):
    # AC-8: error handling unchanged in all-refs mode.
    with pytest.raises(RepositoryError):
        read_commits(str(tmp_path / "nope"), all_refs=True)


def test_all_refs_includes_remote_tracking_branches(remote_tracking_repo: Path):
    # AC-10: commits reachable only from refs/remotes/* appear in all-refs mode
    # but not HEAD-only.
    head = {c.subject for c in read_commits(str(remote_tracking_repo))}
    assert head == {"Local: first"}
    assert "Remote: only-b" not in head

    all_subjects = {
        c.subject for c in read_commits(str(remote_tracking_repo), all_refs=True)
    }
    assert {"Remote: only-a", "Remote: only-b", "Upstream: base"} <= all_subjects


def test_all_refs_order_matches_git_log_with_remotes(remote_tracking_repo: Path):
    # AC-3 including remote-tracking refs.
    expected = _git_log_shas(remote_tracking_repo, 500, all_refs=True)
    actual = [c.sha for c in read_commits(str(remote_tracking_repo), all_refs=True)]
    assert actual == expected


# --- Commit detail (SPEC-003) --------------------------------------------

@pytest.fixture(params=["pygit2", "cli"])
def detail_reader(request, monkeypatch):
    """Yield ``read_commit_detail`` exercised via each backend.

    The ``cli`` variant forces the git-CLI fallback by making the pygit2 path
    raise a non-``RepositoryError`` exception (matches SPEC-001's dual-path
    coverage discipline).
    """
    if request.param == "cli":
        def _boom(*_a, **_k):
            raise RuntimeError("forced CLI fallback")

        monkeypatch.setattr(git_reader, "_read_commit_detail_pygit2", _boom)
    return read_commit_detail


def _sha_by_subject(repo: Path, subject: str) -> str:
    for c in read_commits(str(repo)):
        if c.subject == subject:
            return c.sha
    raise AssertionError(f"no commit with subject {subject!r}")


def _kinds(detail) -> dict[str, str]:
    return {f.path: f.change_kind for f in detail.files}


def test_detail_root_commit_all_added(content_repo: Path, detail_reader):
    sha = _sha_by_subject(content_repo, "root: add files")
    detail = detail_reader(str(content_repo), sha)
    # AC-4: initial commit diffs against the empty tree -> every path is "A".
    assert detail.parents == []
    kinds = _kinds(detail)
    assert kinds == {"a.txt": "A", "b.txt": "A", "dir/c.txt": "A"}
    assert detail.total_files == 3
    assert detail.files_truncated is False


def test_detail_modify_and_full_message(content_repo: Path, detail_reader):
    sha = _sha_by_subject(content_repo, "modify a")
    detail = detail_reader(str(content_repo), sha)
    assert _kinds(detail) == {"a.txt": "M"}
    # AC-2: full message (subject + body) preserved with line breaks.
    assert detail.subject == "modify a"
    assert "Body line one." in detail.message
    assert "Body line two." in detail.message
    assert "\n" in detail.message
    # AC-2/AC-6: author + committer identities and both timestamps.
    assert detail.author_name == "Test User"
    assert detail.committer_email == "test@example.com"
    assert isinstance(detail.authored_timestamp, int)
    assert isinstance(detail.committer_timestamp, int)
    assert len(detail.sha) == 40
    assert detail.short_sha == detail.sha[:7]


def test_detail_delete(content_repo: Path, detail_reader):
    sha = _sha_by_subject(content_repo, "delete b")
    detail = detail_reader(str(content_repo), sha)
    assert _kinds(detail) == {"b.txt": "D"}


def test_detail_rename_sets_old_path(content_repo: Path, detail_reader):
    sha = _sha_by_subject(content_repo, "rename c")
    detail = detail_reader(str(content_repo), sha)
    renamed = [f for f in detail.files if f.change_kind == "R"]
    assert len(renamed) == 1
    f = renamed[0]
    assert f.path == "dir/c_renamed.txt"
    assert f.old_path == "dir/c.txt"
    assert f.old_path != f.path


def test_detail_merge_uses_first_parent(content_repo: Path, detail_reader):
    sha = _sha_by_subject(content_repo, "Merge feature")
    detail = detail_reader(str(content_repo), sha)
    # AC-5: 2-parent merge; file list is the first-parent diff (feature's a.txt).
    assert len(detail.parents) == 2
    assert _kinds(detail) == {"a.txt": "M"}


def test_detail_truncation(many_files_repo: Path, detail_reader):
    sha = _sha_by_subject(many_files_repo, "add many files")
    detail = detail_reader(str(many_files_repo), sha, 200)
    # AC-3: capped at 200 with an accurate total.
    assert len(detail.files) == 200
    assert detail.files_truncated is True
    assert detail.total_files == 250


def test_detail_case_insensitive_and_short_sha(content_repo: Path, detail_reader):
    full = _sha_by_subject(content_repo, "delete b")
    upper_prefix = full[:10].upper()
    detail = detail_reader(str(content_repo), upper_prefix)
    # AC-7: mixed-case short prefix resolves to the same commit, lowercased.
    assert detail.sha == full


def test_detail_unknown_sha_raises_unknown(content_repo: Path, detail_reader):
    # AC-7: well-formed but missing SHA -> UnknownCommitError (maps to 404).
    with pytest.raises(UnknownCommitError):
        detail_reader(str(content_repo), "0" * 40)


def _shortest_ambiguous_prefix(repo: Path) -> str:
    """Shortest hex prefix shared by >=2 objects in ``repo`` (guaranteed
    ambiguous). With more than 16 objects a 1-char collision is certain."""
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--objects", "--all"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    oids = [line.split()[0] for line in out.splitlines() if line]
    for length in range(1, 40):
        seen: set[str] = set()
        for h in oids:
            prefix = h[:length]
            if prefix in seen:
                return prefix
            seen.add(prefix)
    raise AssertionError("no ambiguous prefix found in repo")


def test_detail_ambiguous_prefix_raises_repository_error(content_repo: Path):
    # AC-7 (pygit2 path): a prefix matching multiple objects -> RepositoryError
    # (HTTP 400), NOT UnknownCommitError (404). pygit2 raises ValueError on
    # GIT_EAMBIGUOUS, which read_commit_detail maps to RepositoryError.
    prefix = _shortest_ambiguous_prefix(content_repo)
    with pytest.raises(RepositoryError) as excinfo:
        read_commit_detail(str(content_repo), prefix)
    assert not isinstance(excinfo.value, UnknownCommitError)


def test_classify_commit_error_ambiguous_is_repository_error():
    # CLI-fallback counterpart: git's "short object ID ... is ambiguous" (which
    # also carries an "ambiguous argument ... unknown revision" line) must map
    # to RepositoryError (400), not UnknownCommitError (404).
    stderr = (
        "error: short object ID abcd is ambiguous\n"
        "fatal: ambiguous argument 'abcd': unknown revision or path not in "
        "the working tree"
    )
    err = git_reader._classify_commit_error("/repo", stderr)
    assert isinstance(err, RepositoryError)
    assert not isinstance(err, UnknownCommitError)


def test_classify_commit_error_missing_is_unknown_commit():
    # A well-formed but missing object -> UnknownCommitError (404).
    err = git_reader._classify_commit_error(
        "/repo", "fatal: bad object 0000000000000000000000000000000000000000"
    )
    assert isinstance(err, UnknownCommitError)


def _snapshot_git(repo: Path) -> dict[str, str]:
    gitdir = repo / ".git"
    snap: dict[str, str] = {}
    for p in sorted(gitdir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(gitdir).as_posix()
        if rel.endswith(".lock"):  # transient lock files are not mutations.
            continue
        snap[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def test_detail_is_read_only(content_repo: Path, detail_reader):
    # AC-8: fetching detail mutates nothing under .git/.
    sha = _sha_by_subject(content_repo, "Merge feature")
    before = _snapshot_git(content_repo)
    detail_reader(str(content_repo), sha)
    after = _snapshot_git(content_repo)
    assert before == after


# --- SPEC-004: ref decoration ---------------------------------------------


def _git_for_each_ref_oracle(repo: Path) -> set[tuple[str, str]]:
    """Return the ``(commit_sha, short_ref_name)`` set expected on the repo.

    Enumerates local branches, remote-tracking branches, and tags via
    ``git for-each-ref``. Annotated tags are represented by their **peeled**
    commit (the object they ultimately point at). ``refs/remotes/*/HEAD``
    symbolic aliases are excluded because they name a branch by another name
    rather than a distinct tip. This is the AC-2 oracle.
    """
    out = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "for-each-ref",
            "--format=%(objectname)%00%(refname)%00%(*objectname)%00%(objecttype)%00%(*objecttype)",
            "refs/heads",
            "refs/remotes",
            "refs/tags",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    pairs: set[tuple[str, str]] = set()
    for line in out.splitlines():
        if not line:
            continue
        parts = line.split("\x00")
        if len(parts) < 5:
            continue
        objname, refname, peeled_objname, objtype, peeled_objtype = parts[:5]
        if refname.startswith("refs/remotes/") and refname.endswith("/HEAD"):
            continue
        if peeled_objtype == "commit" and peeled_objname:
            commit_sha = peeled_objname
        elif objtype == "commit":
            commit_sha = objname
        else:
            continue
        for prefix in ("refs/heads/", "refs/remotes/", "refs/tags/"):
            if refname.startswith(prefix):
                pairs.add((commit_sha, refname[len(prefix):]))
                break
    return pairs


@pytest.fixture(params=["pygit2", "cli"])
def decoration_backend(request, monkeypatch):
    """Yield ``read_commits`` exercised via each decoration backend.

    The ``cli`` variant forces the git-CLI fallback by making the pygit2 path
    raise a non-``RepositoryError`` exception (matching SPEC-003's dual-path
    discipline — SPEC-001's CLI fallback was previously never exercised by
    tests, and the SPEC-004 research note calls out this parity as
    "historically weak here").
    """
    if request.param == "cli":
        def _boom(*_a, **_k):
            raise RuntimeError("forced CLI fallback")

        monkeypatch.setattr(git_reader, "_read_pygit2", _boom)
        monkeypatch.setattr(git_reader, "_decoration_pygit2", _boom)
    return read_commits


def _pairs_from_records(records) -> set[tuple[str, str]]:
    return {(r.sha, entry["name"]) for r in records for entry in r.refs if entry["type"] != "head"}


def test_decoration_matches_git_oracle_branched(branched_repo: Path, decoration_backend):
    # AC-2/AC-3: the set of (commit_sha, ref_name) pairs equals git's own
    # for-each-ref oracle (excluding the derived HEAD entry, which is not a
    # ref of its own). Set equality — not ordering — per the research note.
    records = decoration_backend(str(branched_repo), all_refs=True)
    expected = _git_for_each_ref_oracle(branched_repo)
    assert _pairs_from_records(records) == expected


def test_decoration_matches_git_oracle_tags(tagged_side_history_repo: Path, decoration_backend):
    # Annotated tags must decorate the peeled commit (AC-3) so both backends
    # end up equal to git's oracle on a tagged-side-history repo.
    records = decoration_backend(str(tagged_side_history_repo), all_refs=True)
    expected = _git_for_each_ref_oracle(tagged_side_history_repo)
    assert _pairs_from_records(records) == expected


def test_decoration_matches_git_oracle_remote_tracking(
    remote_tracking_repo: Path, decoration_backend
):
    records = decoration_backend(str(remote_tracking_repo), all_refs=True)
    expected = _git_for_each_ref_oracle(remote_tracking_repo)
    assert _pairs_from_records(records) == expected


def test_undecorated_commits_have_empty_refs(linear_repo: Path, decoration_backend):
    # AC-1 shape: commits that no ref points at directly carry an empty list.
    records = decoration_backend(str(linear_repo))
    # HEAD (== main) sits on the newest commit; everything older is
    # undecorated.
    tip, *rest = records
    assert tip.refs, "tip commit should carry at least the main branch entry"
    for r in rest:
        assert r.refs == [], f"expected empty refs on {r.sha}, got {r.refs}"


def test_tip_only_semantics(branched_repo: Path, decoration_backend):
    # AC-2: a ref labels ONLY the commit it points directly at, never every
    # reachable ancestor. `main` on the merge commit must NOT surface on the
    # merge's parents even though those parents are reachable from `main`.
    records = decoration_backend(str(branched_repo), all_refs=True)
    main_holders = [r.sha for r in records if any(e["name"] == "main" for e in r.refs)]
    assert len(main_holders) == 1, f"expected exactly one 'main'-decorated commit, got {main_holders}"


def test_type_and_shorthand_mapping(remote_tracking_repo: Path, decoration_backend):
    # AC-3: refs/heads/main -> {name:"main", type:"branch"};
    # refs/remotes/up/remote-feature -> {name:"up/remote-feature", type:"remote"}.
    records = decoration_backend(str(remote_tracking_repo), all_refs=True)
    seen: dict[str, str] = {}
    for r in records:
        for entry in r.refs:
            seen[entry["name"]] = entry["type"]
    assert seen.get("main") == "branch"
    # The upstream's default branch is fetched as up/main.
    assert seen.get("up/main") == "remote"
    assert seen.get("up/remote-feature") == "remote"
    # No refname retains the "refs/heads/" or "refs/remotes/" prefix.
    for name in seen:
        assert not name.startswith("refs/"), f"short name should not carry namespace: {name}"


def test_annotated_tag_peels_to_commit(tagged_side_history_repo: Path, decoration_backend):
    # AC-3: an annotated tag decorates the commit it peels to (not the tag
    # object itself). Verify by finding `v1-side` in the returned decoration
    # and checking that SHA resolves to a commit via `git rev-parse`.
    records = decoration_backend(str(tagged_side_history_repo), all_refs=True)
    holder = next(
        (r for r in records if any(e["name"] == "v1-side" for e in r.refs)),
        None,
    )
    assert holder is not None, "v1-side tag decoration missing"
    kinds = subprocess.run(
        ["git", "-C", str(tagged_side_history_repo), "cat-file", "-t", holder.sha],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    assert kinds == "commit"


def test_remote_head_alias_excluded(remote_tracking_repo: Path, decoration_backend):
    # AC-3: refs/remotes/up/HEAD is a symbolic alias for up/main and must be
    # filtered out (otherwise it duplicates up/main under a different name).
    # `git remote set-head` writes that alias; we invoke it inline here.
    subprocess.run(
        ["git", "-C", str(remote_tracking_repo), "remote", "set-head", "up", "main"],
        check=True,
        capture_output=True,
    )
    records = decoration_backend(str(remote_tracking_repo), all_refs=True)
    names = {e["name"] for r in records for e in r.refs}
    assert "up/HEAD" not in names, f"expected up/HEAD alias to be filtered, saw {names}"


def test_head_attached_marks_branch_entry(branched_repo: Path, decoration_backend):
    # AC-4: attached HEAD marks the matching branch entry is_head=True; no
    # separate HEAD entry is emitted.
    records = decoration_backend(str(branched_repo), all_refs=True)
    head_entries = [(r.sha, e) for r in records for e in r.refs if e.get("is_head")]
    assert len(head_entries) == 1, f"expected exactly one is_head entry, got {head_entries}"
    _, entry = head_entries[0]
    assert entry["type"] == "branch"
    assert entry["name"] == "main"
    # No dedicated {type:"head"} entry when HEAD is attached.
    head_type_entries = [e for r in records for e in r.refs if e["type"] == "head"]
    assert head_type_entries == []


def test_head_detached_emits_dedicated_head_entry(detached_head_repo: Path, decoration_backend):
    # AC-4: detached HEAD adds {name:"HEAD", type:"head", is_head:true}
    # on the pointed-at commit; no branch entry is marked is_head.
    records = decoration_backend(str(detached_head_repo), all_refs=True)
    head_entries = [
        (r.sha, e) for r in records for e in r.refs if e["type"] == "head"
    ]
    assert len(head_entries) == 1, head_entries
    sha, entry = head_entries[0]
    assert entry == {"name": "HEAD", "type": "head", "is_head": True}
    # No branch entry should carry is_head=True in detached mode.
    branch_head = [
        e for r in records for e in r.refs if e["type"] == "branch" and e.get("is_head")
    ]
    assert branch_head == []
    # The detached commit also carries the "pin" tag (proves head + tag
    # coexist on the same commit — AC-5 rendering with multiple entries).
    holder = next(r for r in records if r.sha == sha)
    tag_names = {e["name"] for e in holder.refs if e["type"] == "tag"}
    assert "pin" in tag_names


def test_multi_ref_tip_carries_all_entries(multi_ref_tip_repo: Path, decoration_backend):
    # AC-5/AC-6: one commit can carry a mix of branch + lightweight tag +
    # annotated tag entries simultaneously; each is a distinct entry.
    records = decoration_backend(str(multi_ref_tip_repo), all_refs=True)
    tip = next(r for r in records if r.subject == "tip: all-refs on me")
    entries = {(e["name"], e["type"]) for e in tip.refs}
    assert ("main", "branch") in entries
    assert ("release", "branch") in entries
    assert ("light-tag", "tag") in entries
    assert ("v1.0", "tag") in entries


def test_decoration_populated_in_head_only_mode(branched_repo: Path, decoration_backend):
    # AC-7: decoration is orthogonal to the walk mode. Even in HEAD-only mode
    # the returned records carry their tip refs (main + HEAD indicator).
    records = decoration_backend(str(branched_repo), all_refs=False)
    tip = records[0]
    names = {e["name"] for e in tip.refs}
    assert "main" in names
    assert any(e.get("is_head") for e in tip.refs)


def test_refs_outside_window_are_omitted(unmerged_repo: Path, decoration_backend):
    # AC-7: refs whose tip is not in the returned window simply do not appear
    # — no dangling or fabricated entries. In HEAD-only mode of unmerged_repo,
    # the `feature` branch tip is unreachable, so no record should carry a
    # `feature` entry.
    records = decoration_backend(str(unmerged_repo), all_refs=False)
    names = {e["name"] for r in records for e in r.refs}
    assert "feature" not in names
    # Sanity: main + HEAD do appear.
    assert "main" in names


def _snapshot_git_for_decoration(repo: Path) -> dict[str, str]:
    """.git/ hash snapshot for read-only assertions (mirrors ``_snapshot_git``)."""
    gitdir = repo / ".git"
    snap: dict[str, str] = {}
    for p in sorted(gitdir.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(gitdir).as_posix()
        if rel.endswith(".lock"):
            continue
        snap[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def test_decoration_is_read_only(tagged_side_history_repo: Path, decoration_backend):
    # AC-8: enumerating refs must not mutate .git/ (no refs written, no
    # objects added, no index touched).
    before = _snapshot_git_for_decoration(tagged_side_history_repo)
    decoration_backend(str(tagged_side_history_repo), all_refs=True)
    after = _snapshot_git_for_decoration(tagged_side_history_repo)
    assert before == after


def test_dual_backend_parity(branched_repo: Path):
    # Both backends must return equal decoration maps for the same repo,
    # so tests that check via one backend are meaningful for the other.
    pygit_map = git_reader._decoration_pygit2(str(branched_repo))
    cli_map = git_reader._decoration_git(str(branched_repo))
    # Normalize by sorting entry lists (order within a commit is not part of
    # the contract; the tests assert set-equality).
    def norm(m):
        return {sha: sorted(entries, key=lambda e: (e["type"], e["name"])) for sha, entries in m.items()}
    assert norm(pygit_map) == norm(cli_map)


def test_empty_repo_returns_empty_decoration(empty_repo: Path):
    # An unborn HEAD has no refs and no HEAD entry to add — decoration is
    # empty and read_commits returns []. Regression guard. Uses the primary
    # (pygit2) path only: the CLI fallback's unborn-HEAD handling is a
    # separate concern (``git log`` exits non-zero with "does not have any
    # commits yet" and would be mapped to RepositoryError) outside SPEC-004
    # scope.
    records = read_commits(str(empty_repo))
    assert records == []
