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


# --- all-refs mode (SPEC-002) ------------------------------------------------


def _edges_reference_only_real_parents(commits, graph) -> None:
    parents_by_sha = {c.sha: set(c.parents) for c in commits}
    for node in graph["commits"]:
        for edge in node["edges"]:
            assert edge["parent"] in parents_by_sha[node["sha"]]


def test_unmerged_branches_distinct_lanes_no_fabricated_merge(unmerged_repo: Path):
    # AC-4: two branches that never merged occupy distinct lanes with no
    # fabricated merge edge (this fixture has no real merges).
    commits = read_commits(str(unmerged_repo), all_refs=True)
    graph = build_graph(commits)
    assert graph["lane_count"] >= 2
    _edges_reference_only_real_parents(commits, graph)
    # No merge exists, so no commit may have more than one outgoing edge.
    assert all(len(node["edges"]) <= 1 for node in graph["commits"])
    lanes = {node["lane"] for node in graph["commits"]}
    assert len(lanes) >= 2


def test_disconnected_histories_own_lanes_no_cross_edges(orphan_repo: Path):
    # AC-5: independent histories each render, with no edge between them.
    commits = read_commits(str(orphan_repo), all_refs=True)
    graph = build_graph(commits)
    _edges_reference_only_real_parents(commits, graph)
    roots = [c for c in commits if not c.parents]
    assert len(roots) == 2  # two disconnected roots
    # Each root ends its own lane and emits no edges.
    root_shas = {c.sha for c in roots}
    for node in graph["commits"]:
        if node["sha"] in root_shas:
            assert node["edges"] == []


def test_all_refs_boundary_edges_for_capped_parents(unmerged_repo: Path):
    # AC-6: parents beyond the cap are boundary edges in all-refs mode too.
    commits = read_commits(str(unmerged_repo), max_commits=2, all_refs=True)
    graph = build_graph(commits)
    boundary = [e for c in graph["commits"] for e in c["edges"] if e["boundary"]]
    assert boundary, "expected boundary edges for truncated all-refs history"


def test_equal_timestamp_lanes_valid(equal_timestamp_repo: Path):
    # Sanity: with equal-timestamp sibling tips the lane algorithm still only
    # ever routes edges to real parents (no reliance on parent-before-child).
    commits = read_commits(str(equal_timestamp_repo), all_refs=True)
    graph = build_graph(commits)
    _edges_reference_only_real_parents(commits, graph)
    assert graph["lane_count"] >= 2
