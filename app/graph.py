"""Assign commits to horizontal lanes and colors for graph rendering.

Implements the canonical greedy, newest-first column-reservation pass (see
`git`'s ``graph.c`` and the pvigier/git-cola precedents): walk commits from
newest to oldest, keep a list of active lanes, let the **first parent inherit
the commit's lane**, give extra (merge) parents free or newly-appended lanes,
reuse freed lanes, and route edges to each parent's lane.

Parents that fall outside the fetched window (AC-9 cap) are marked as boundary
edges so the frontend can draw a stub trailing off-screen instead of dangling
(AC-4 ∩ AC-9). Colors cycle a colorblind-safe Okabe–Ito palette by lane index.
"""

from __future__ import annotations

from app.git_reader import CommitRecord

# Okabe–Ito colorblind-safe categorical palette (8 hues), cycled by lane index.
PALETTE = [
    "#0072B2",  # blue
    "#E69F00",  # orange
    "#009E73",  # green
    "#D55E00",  # vermillion
    "#CC79A7",  # reddish purple
    "#56B4E9",  # sky blue
    "#F0E442",  # yellow
    "#999999",  # grey
]


def _color(lane: int) -> str:
    return PALETTE[lane % len(PALETTE)]


def _first_free(lanes: list[str | None]) -> int | None:
    for i, occupant in enumerate(lanes):
        if occupant is None:
            return i
    return None


def _claim_lane(lanes: list[str | None], sha: str) -> int:
    """Reserve a lane for ``sha``: reuse the leftmost free slot, else append."""
    slot = _first_free(lanes)
    if slot is None:
        lanes.append(sha)
        return len(lanes) - 1
    lanes[slot] = sha
    return slot


def build_graph(commits: list[CommitRecord]) -> dict:
    """Return ``{"lane_count": int, "commits": [commit dict + lane/color/edges]}``.

    Input must be in display order (newest-first), as produced by
    :func:`app.git_reader.read_commits`.
    """
    in_window = {c.sha for c in commits}
    lanes: list[str | None] = []  # lanes[i] = sha expected next in column i.
    lane_count = 0
    laid_out: list[dict] = []

    for commit in commits:
        sha = commit.sha

        # Find lanes already reserved for this commit by earlier (newer) children.
        reserved = [i for i, occupant in enumerate(lanes) if occupant == sha]
        if reserved:
            my_lane = reserved[0]
            # Merge convergence: other lanes waiting for this commit collapse here.
            for extra in reserved[1:]:
                lanes[extra] = None
        else:
            # A tip within the window (newest commit or an in-window branch head).
            my_lane = _claim_lane(lanes, sha)

        edges: list[dict] = []
        parents = commit.parents
        if not parents:
            # Root commit ends its lane.
            lanes[my_lane] = None
        else:
            # First parent continues in this commit's lane.
            first_parent = parents[0]
            lanes[my_lane] = first_parent
            edges.append(_edge(first_parent, my_lane, in_window))
            # Additional (merge) parents reuse their existing lane or take a new one.
            for parent in parents[1:]:
                existing = next(
                    (i for i, occupant in enumerate(lanes) if occupant == parent),
                    None,
                )
                to_lane = existing if existing is not None else _claim_lane(lanes, parent)
                edges.append(_edge(parent, to_lane, in_window))

        lane_count = max(lane_count, len(lanes))
        record = commit.to_dict()
        record["lane"] = my_lane
        record["color"] = _color(my_lane)
        record["edges"] = edges
        laid_out.append(record)

    return {"lane_count": lane_count, "commits": laid_out}


def _edge(parent: str, to_lane: int, in_window: set[str]) -> dict:
    return {
        "parent": parent,
        "to_lane": to_lane,
        "color": _color(to_lane),
        "boundary": parent not in in_window,
    }
