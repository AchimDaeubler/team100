"""Tests for app.graph lane assignment (AC-4, AC-5, AC-6, AC-9 boundary)."""

from __future__ import annotations

from pathlib import Path

from app.git_reader import CommitRecord, read_commits
from app.graph import build_graph


def _c(sha: str, parents: list[str]) -> CommitRecord:
    return CommitRecord(sha, sha[:7], parents, f"msg {sha}", "a", "a@b", 0)


def test_linear_history_single_lane(linear_repo: Path):
    graph = build_graph(read_commits(str(linear_repo)))
    assert graph["lane_count"] == 1  # AC-6
    assert all(c["lane"] == 0 for c in graph["commits"])


def test_branch_uses_distinct_lanes_and_colors(branched_repo: Path):
    graph = build_graph(read_commits(str(branched_repo)))
    assert graph["lane_count"] >= 2  # AC-5 parallel branches occupy separate lanes
    lanes = {c["lane"] for c in graph["commits"]}
    assert len(lanes) >= 2
    colors = {c["color"] for c in graph["commits"]}
    assert len(colors) >= 2  # distinct colors per lane


def test_merge_edges_connect_to_all_parents():
    # AC-4: merge commit must have an edge to each parent.
    commits = [
        _c("M", ["C", "D"]),
        _c("D", ["B"]),
        _c("C", ["B"]),
        _c("B", ["A"]),
        _c("A", []),
    ]
    graph = build_graph(commits)
    merge = graph["commits"][0]
    assert merge["sha"] == "M"
    assert {e["parent"] for e in merge["edges"]} == {"C", "D"}
    # The two parents route to different lanes (fan-out), then converge at B.
    to_lanes = {e["to_lane"] for e in merge["edges"]}
    assert len(to_lanes) == 2


def test_octopus_merge_connects_three_parents(octopus_repo: Path):
    graph = build_graph(read_commits(str(octopus_repo)))
    merge = graph["commits"][0]
    assert len(merge["edges"]) == 3  # AC-4


def test_boundary_edges_for_parents_outside_window(branched_repo: Path):
    # AC-4 ∩ AC-9: parents beyond the cap are flagged boundary, not dangling.
    commits = read_commits(str(branched_repo), max_commits=2)
    graph = build_graph(commits)
    boundary_edges = [e for c in graph["commits"] for e in c["edges"] if e["boundary"]]
    assert boundary_edges, "expected at least one boundary edge for truncated history"


def test_root_commit_has_no_edges(linear_repo: Path):
    graph = build_graph(read_commits(str(linear_repo)))
    assert graph["commits"][-1]["edges"] == []
