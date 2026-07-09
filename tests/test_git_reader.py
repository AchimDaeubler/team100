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
