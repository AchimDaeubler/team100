"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

const ROW_H = 28; // vertical spacing between commit rows
const LANE_W = 16; // horizontal spacing between lanes
const PAD_X = 16; // left padding before lane 0
const NODE_R = 4.5; // commit node radius
const TEXT_GAP = 18; // gap between the lane area and the text column

function laneX(lane) {
  return PAD_X + lane * LANE_W;
}
function rowY(row) {
  return ROW_H / 2 + row * ROW_H;
}

function el(name, attrs, text) {
  const node = document.createElementNS(SVG_NS, name);
  for (const [k, v] of Object.entries(attrs || {})) node.setAttribute(k, v);
  if (text != null) node.textContent = text;
  return node;
}

function fmtDate(unixSeconds) {
  const d = new Date(unixSeconds * 1000);
  return d.toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

// Build the SVG path for an edge from a child node to one of its parents.
// The line travels in `toLane`, branching out from the child lane near the top
// and converging into the parent's actual lane near the bottom.
function edgePath(cX, cY, toX, endX, endY) {
  const branch = toX !== cX;
  const converge = endX !== toX;
  let topBend = cY + (branch ? ROW_H : 0);
  let botBend = endY - (converge ? ROW_H : 0);
  if (topBend > botBend) {
    const mid = (topBend + botBend) / 2;
    topBend = botBend = mid;
  }
  let d = `M ${cX} ${cY} `;
  if (branch) {
    d += `C ${cX} ${cY + ROW_H * 0.4} ${toX} ${cY + ROW_H * 0.55} ${toX} ${topBend} `;
  }
  d += `L ${toX} ${botBend} `;
  if (converge) {
    d += `C ${toX} ${endY - ROW_H * 0.55} ${endX} ${endY - ROW_H * 0.4} ${endX} ${endY} `;
  } else {
    d += `L ${endX} ${endY} `;
  }
  return d;
}

function render(data) {
  document.getElementById("repo").textContent = data.repo || "";
  const graph = document.getElementById("graph");
  graph.innerHTML = "";

  const commits = data.commits || [];
  const laneCount = data.lane_count || 1;
  const rowOf = new Map();
  const laneOf = new Map();
  commits.forEach((c, i) => {
    rowOf.set(c.sha, i);
    laneOf.set(c.sha, c.lane);
  });

  const graphWidth = laneX(laneCount - 1) + PAD_X;
  const textX = graphWidth + TEXT_GAP;
  const height = commits.length * ROW_H;
  const width = Math.max(textX + 640, 900);
  const bottomY = height;

  const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}` });

  // Edges first (drawn behind the nodes).
  commits.forEach((c) => {
    const cX = laneX(c.lane);
    const cY = rowY(rowOf.get(c.sha));
    (c.edges || []).forEach((e) => {
      const toX = laneX(e.to_lane);
      let endX = toX;
      let endY = bottomY;
      if (!e.boundary && rowOf.has(e.parent)) {
        endX = laneX(laneOf.get(e.parent));
        endY = rowY(rowOf.get(e.parent));
      }
      const path = el("path", {
        class: "edge",
        d: edgePath(cX, cY, toX, endX, endY),
        stroke: e.color,
      });
      if (e.boundary) path.setAttribute("stroke-dasharray", "4 4");
      svg.appendChild(path);
    });
  });

  // Row hit areas + nodes + text.
  commits.forEach((c, i) => {
    const y = rowY(i);
    const hit = el("rect", {
      class: "row-hit",
      x: 0,
      y: i * ROW_H,
      width,
      height: ROW_H,
    });
    hit.appendChild(el("title", {}, `${c.sha}\n${c.subject}\n${c.author_name} <${c.author_email}>\n${fmtDate(c.authored_timestamp)}`));
    svg.appendChild(hit);

    svg.appendChild(el("circle", { class: "node", cx: laneX(c.lane), cy: y, r: NODE_R, fill: c.color }));

    svg.appendChild(el("text", { class: "sha", x: textX, y, "dominant-baseline": "central", fill: c.color }, c.short_sha));
    svg.appendChild(el("text", { class: "subject", x: textX + 64, y, "dominant-baseline": "central" }, c.subject));
    svg.appendChild(
      el("text", { class: "meta", x: width - 12, y, "dominant-baseline": "central", "text-anchor": "end" }, `${c.author_name} · ${fmtDate(c.authored_timestamp)}`)
    );
  });

  graph.appendChild(svg);
}

function showError(message) {
  const box = document.getElementById("error");
  box.textContent = "Error: " + message;
  box.hidden = false;
}

fetch("/api/commits")
  .then((r) => r.json().then((body) => ({ ok: r.ok, body })))
  .then(({ ok, body }) => {
    if (!ok || body.error) {
      showError(body.error || "failed to load commits");
      return;
    }
    if (!body.commits || body.commits.length === 0) {
      showError("No commits found in this repository.");
      return;
    }
    render(body);
  })
  .catch((err) => showError(String(err)));
