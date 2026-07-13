"use strict";

const SVG_NS = "http://www.w3.org/2000/svg";

// Map of full SHA -> row index for the commits currently in the graph window.
// Used to decide whether a parent SHA is clickable (SPEC-001 boundary-edge
// convention: only parents inside the fetched window are links).
let ROW_OF = new Map();
let LAST_TRIGGER = null; // row element that opened the panel (focus restore).

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
  ROW_OF = rowOf;

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
      "data-sha": c.sha,
      tabindex: "0",
      role: "button",
      "aria-label": `Commit ${c.short_sha}: ${c.subject}`,
    });
    hit.appendChild(el("title", {}, `${c.sha}\n${c.subject}\n${c.author_name} <${c.author_email}>\n${fmtDate(c.authored_timestamp)}`));
    svg.appendChild(hit);

    svg.appendChild(el("circle", { class: "node", "data-sha": c.sha, cx: laneX(c.lane), cy: y, r: NODE_R, fill: c.color }));

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

function setSelected(sha) {
  document
    .querySelectorAll(".row-hit.selected, .node.selected")
    .forEach((n) => n.classList.remove("selected"));
  if (!sha) return;
  document
    .querySelectorAll(`[data-sha="${sha}"]`)
    .forEach((n) => n.classList.add("selected"));
}

function makeMetaRow(dl, label, valueNode) {
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  if (typeof valueNode === "string") dd.textContent = valueNode;
  else dd.appendChild(valueNode);
  dl.appendChild(dt);
  dl.appendChild(dd);
}

function renderParents(parents) {
  const frag = document.createDocumentFragment();
  if (!parents || parents.length === 0) {
    const span = document.createElement("span");
    span.className = "parent-inert";
    span.textContent = "(root commit)";
    frag.appendChild(span);
    return frag;
  }
  parents.forEach((p, idx) => {
    if (idx > 0) frag.appendChild(document.createTextNode("  "));
    const short = p.slice(0, 7);
    if (ROW_OF.has(p)) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "parent-link";
      btn.textContent = short;
      btn.addEventListener("click", () => openDetail(p));
      frag.appendChild(btn);
    } else {
      const span = document.createElement("span");
      span.className = "parent-inert";
      span.textContent = short;
      span.title = "parent outside the current graph window";
      frag.appendChild(span);
    }
  });
  return frag;
}

function populateDetail(d) {
  document.getElementById("detail-title").textContent = `Commit ${d.short_sha}`;

  const meta = document.getElementById("detail-meta");
  meta.innerHTML = "";
  const shaSpan = document.createElement("span");
  shaSpan.className = "mono detail-sha";
  shaSpan.textContent = d.sha;
  makeMetaRow(meta, "SHA", shaSpan);
  makeMetaRow(meta, "Author", `${d.author_name} <${d.author_email}>`);
  makeMetaRow(meta, "Authored", fmtDate(d.authored_timestamp));
  makeMetaRow(meta, "Committer", `${d.committer_name} <${d.committer_email}>`);
  makeMetaRow(meta, "Committed", fmtDate(d.committer_timestamp));
  makeMetaRow(meta, "Parents", renderParents(d.parents));

  document.getElementById("detail-message").textContent = d.message || "";

  const filesTitle = document.getElementById("detail-files-title");
  const base = `Files changed (${d.total_files})`;
  filesTitle.textContent =
    d.parents && d.parents.length >= 2
      ? `${base} — vs ${d.parents[0].slice(0, 7)}`
      : base;

  const list = document.getElementById("detail-files");
  list.innerHTML = "";
  (d.files || []).forEach((f) => {
    const li = document.createElement("li");
    const kind = document.createElement("span");
    kind.className = `change-kind change-${f.change_kind[0]}`;
    kind.textContent = f.change_kind;
    kind.title = f.change_kind;
    const path = document.createElement("span");
    path.className = "file-path";
    path.textContent = f.path;
    li.appendChild(kind);
    li.appendChild(path);
    if (f.old_path) {
      const old = document.createElement("span");
      old.className = "file-old";
      old.textContent = `(was ${f.old_path})`;
      li.appendChild(old);
    }
    list.appendChild(li);
  });
  if (d.files_truncated) {
    const li = document.createElement("li");
    li.className = "detail-more";
    li.textContent = `… and ${d.total_files - (d.files || []).length} more`;
    list.appendChild(li);
  }
}

function openDetail(sha) {
  const dialog = document.getElementById("detail");
  // Focus the trigger row first so the native <dialog> restores focus to it
  // on close (AC-10).
  const trigger = document.querySelector(`.row-hit[data-sha="${sha}"]`);
  if (trigger) {
    LAST_TRIGGER = trigger;
    trigger.focus();
  }
  setSelected(sha);
  fetch(`/api/commits/${sha}`)
    .then((r) => r.json().then((body) => ({ ok: r.ok, body })))
    .then(({ ok, body }) => {
      if (!ok || body.error) {
        showError(body.error || "failed to load commit detail");
        return;
      }
      populateDetail(body);
      // showModal() gives us AC-10's modal focus trap for free, at the cost of
      // making the underlying graph inert while open (a tradeoff vs AC-9's
      // literal "SVG stays scrollable"). AC-9's core intent still holds: the
      // graph does not reflow and the selected row stays highlighted, and the
      // drawer overlays rather than resizing the SVG.
      if (!dialog.open) dialog.showModal();
    })
    .catch((err) => showError(String(err)));
}

function initDetailPanel() {
  const dialog = document.getElementById("detail");
  const graph = document.getElementById("graph");

  document
    .getElementById("detail-close")
    .addEventListener("click", () => dialog.close());

  // Click on the backdrop (outside the panel content) closes it.
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });

  // Escape closes the panel. The native <dialog> already does this for real
  // key input, but an explicit handler makes it deterministic; the "close"
  // event below then clears selection and restores focus (AC-10).
  dialog.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      dialog.close();
    }
  });

  // The <dialog> also provides the focus trap; clear selection on close and
  // restore focus to the trigger row.
  dialog.addEventListener("close", () => {
    setSelected(null);
    if (LAST_TRIGGER && document.body.contains(LAST_TRIGGER)) {
      LAST_TRIGGER.focus();
    }
    LAST_TRIGGER = null;
  });

  const shaFromEvent = (e) => {
    const t = e.target;
    return t && t.getAttribute ? t.getAttribute("data-sha") : null;
  };

  graph.addEventListener("click", (e) => {
    const sha = shaFromEvent(e);
    if (sha) openDetail(sha);
  });

  graph.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const sha = shaFromEvent(e);
    if (sha) {
      e.preventDefault();
      openDetail(sha);
    }
  });
}

initDetailPanel();

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
