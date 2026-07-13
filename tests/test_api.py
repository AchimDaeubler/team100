"""Tests for the /api/commits endpoint (AC-1, AC-7, AC-8, AC-9)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.git_reader import read_commits
from app.server import create_app


def _client(repo: Path, max_commits: int = 500, all_refs: bool = False) -> TestClient:
    return TestClient(
        create_app(
            Settings(repo_path=str(repo), max_commits=max_commits, all_refs=all_refs)
        )
    )


def test_commits_endpoint_returns_required_fields(branched_repo: Path):
    resp = _client(branched_repo).get("/api/commits")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 6
    assert body["lane_count"] >= 2
    commit = body["commits"][0]
    # AC-7: each commit exposes the documented fields.
    for field in ("sha", "parents", "subject", "author_name", "author_email", "authored_timestamp"):
        assert field in commit
    assert isinstance(commit["parents"], list)


def test_commits_newest_first(linear_repo: Path):
    body = _client(linear_repo).get("/api/commits").json()
    assert [c["subject"] for c in body["commits"]] == ["third", "second", "first"]  # AC-3


def test_cap_applied(branched_repo: Path):
    body = _client(branched_repo, max_commits=3).get("/api/commits").json()
    assert body["count"] == 3  # AC-9


def test_index_page_served(linear_repo: Path):
    resp = _client(linear_repo).get("/")
    assert resp.status_code == 200
    assert "Commit Graph" in resp.text  # AC-1: UI is served


def test_empty_repo_returns_empty_graph(empty_repo: Path):
    body = _client(empty_repo).get("/api/commits").json()
    assert body["count"] == 0
    assert body["commits"] == []


def test_bad_repo_returns_clean_error(tmp_path: Path):
    body_resp = _client(tmp_path / "nope").get("/api/commits")
    assert body_resp.status_code == 400  # AC-8: clear error, no crash
    assert "error" in body_resp.json()


# --- all-refs mode (SPEC-002) ------------------------------------------------


def test_head_mode_is_default_and_reported(linear_repo: Path):
    # AC-7: HEAD-only remains the default and is surfaced in the metadata.
    body = _client(linear_repo).get("/api/commits").json()
    assert body["refs"] == "head"


def test_all_refs_mode_returns_extra_commits(unmerged_repo: Path):
    # AC-1: all-refs mode exposes commits unreachable from HEAD.
    head_body = _client(unmerged_repo).get("/api/commits").json()
    assert head_body["count"] == 3
    assert head_body["refs"] == "head"

    all_body = _client(unmerged_repo, all_refs=True).get("/api/commits").json()
    assert all_body["count"] == 5  # AC-1
    assert all_body["refs"] == "all"  # AC-7
    subjects = {c["subject"] for c in all_body["commits"]}
    assert {"Feature: work a", "Feature: work b"} <= subjects


def test_all_refs_bad_repo_returns_clean_error(tmp_path: Path):
    # AC-8: bad-repo path still returns the clear 400 in all-refs mode.
    resp = _client(tmp_path / "nope", all_refs=True).get("/api/commits")
    assert resp.status_code == 400
    assert "error" in resp.json()


def test_all_refs_includes_remote_tracking_commits(remote_tracking_repo: Path):
    # AC-10: remote-tracking-only commits surface through the API in all-refs.
    head_body = _client(remote_tracking_repo).get("/api/commits").json()
    all_body = _client(remote_tracking_repo, all_refs=True).get("/api/commits").json()
    assert all_body["count"] > head_body["count"]
    subjects = {c["subject"] for c in all_body["commits"]}
    assert "Remote: only-b" in subjects


# --- Commit detail endpoint (SPEC-003) -----------------------------------

_DETAIL_FIELDS = (
    "sha",
    "short_sha",
    "parents",
    "subject",
    "message",
    "author_name",
    "author_email",
    "authored_timestamp",
    "committer_name",
    "committer_email",
    "committer_timestamp",
    "files",
    "files_truncated",
    "total_files",
)


def _sha_by_subject(repo: Path, subject: str) -> str:
    for c in read_commits(str(repo)):
        if c.subject == subject:
            return c.sha
    raise AssertionError(f"no commit with subject {subject!r}")


def test_detail_endpoint_full_field_set(content_repo: Path):
    sha = _sha_by_subject(content_repo, "modify a")
    resp = _client(content_repo).get(f"/api/commits/{sha}")
    assert resp.status_code == 200  # AC-6
    body = resp.json()
    for field in _DETAIL_FIELDS:
        assert field in body, field
    assert body["sha"] == sha
    assert body["files"] == [{"path": "a.txt", "change_kind": "M"}]
    # old_path is omitted for non-rename entries (AC-6).
    assert "old_path" not in body["files"][0]


def test_detail_rename_includes_old_path(content_repo: Path):
    sha = _sha_by_subject(content_repo, "rename c")
    body = _client(content_repo).get(f"/api/commits/{sha}").json()
    rename = next(f for f in body["files"] if f["change_kind"] == "R")
    assert rename["old_path"] == "dir/c.txt"
    assert rename["path"] == "dir/c_renamed.txt"


def test_detail_merge_reports_first_parent(content_repo: Path):
    sha = _sha_by_subject(content_repo, "Merge feature")
    body = _client(content_repo).get(f"/api/commits/{sha}").json()
    # AC-5: the UI's "vs <short-sha>" label is derived from parents[0].
    assert len(body["parents"]) == 2
    assert body["files"] == [{"path": "a.txt", "change_kind": "M"}]


def test_detail_short_sha_prefix_resolves(content_repo: Path):
    full = _sha_by_subject(content_repo, "delete b")
    body = _client(content_repo).get(f"/api/commits/{full[:7]}").json()
    assert body["sha"] == full  # AC-7: short prefix resolves


def test_detail_mixed_case_sha(content_repo: Path):
    full = _sha_by_subject(content_repo, "delete b")
    mixed = full[:10].upper()
    body = _client(content_repo).get(f"/api/commits/{mixed}").json()
    assert body["sha"] == full  # AC-7: any-case input normalized


def test_detail_unknown_sha_returns_404(content_repo: Path):
    resp = _client(content_repo).get("/api/commits/" + "0" * 40)
    assert resp.status_code == 404  # AC-7
    assert "error" in resp.json()


def test_detail_malformed_sha_returns_400(content_repo: Path):
    resp = _client(content_repo).get("/api/commits/zzzz")
    assert resp.status_code == 400  # AC-7: envelope is {"error": ...}, not 422
    assert "error" in resp.json()


def test_list_endpoint_shape_unchanged(branched_repo: Path):
    # Regression guard: SPEC-001's /api/commits response shape is intact.
    body = _client(branched_repo).get("/api/commits").json()
    assert set(body.keys()) == {
        "repo",
        "max_commits",
        "count",
        "lane_count",
        "commits",
        "refs",  # added by SPEC-002 (all-refs mode); still additive
    }
    commit = body["commits"][0]
    for field in ("sha", "short_sha", "parents", "subject", "lane", "color", "edges"):
        assert field in commit
