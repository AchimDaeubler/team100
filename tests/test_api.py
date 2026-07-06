"""Tests for the /api/commits endpoint (AC-1, AC-7, AC-8, AC-9)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.server import create_app


def _client(repo: Path, max_commits: int = 500) -> TestClient:
    return TestClient(create_app(Settings(repo_path=str(repo), max_commits=max_commits)))


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


def test_bad_repo_returns_clean_error(tmp_path: Path):
    body_resp = _client(tmp_path / "nope").get("/api/commits")
    assert body_resp.status_code == 400  # AC-8: clear error, no crash
    assert "error" in body_resp.json()
