"""Tests for app.git_reader (AC-2, AC-3, AC-7, AC-8, AC-9)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.git_reader import RepositoryError, read_commits


def _git_log_shas(repo: Path, max_count: int) -> list[str]:
    out = subprocess.run(
        ["git", "-C", str(repo), "log", f"--max-count={max_count}", "--pretty=format:%H"],
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
