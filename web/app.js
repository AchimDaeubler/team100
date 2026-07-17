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
const BADGE_GAP = 6; // gap between adjacent badges and between badges & subject
const BADGE_PAD_X = 6; // horizontal padding inside a badge
const BADGE_H = 16; // badge height
const BADGE_MAX_CH = 22; // max characters shown per badge before ellipsis

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

function truncateRefName(name) {
  return name.length > BADGE_MAX_CH ? name.slice(0, BADGE_MAX_CH - 1) + "…" : name;
}

// SPEC-004: collapse an attached-HEAD's dedicated head entry into its branch
// entry so the row renders "HEAD → main" as one combined badge. Detached
// HEAD has no matching branch entry and stays as a standalone head badge.
// Order (deterministic UI choice, not a git-order oracle):
//   1. HEAD (whether combined with its branch or standalone)
//   2. remaining local branches
//   3. remote-tracking branches
//   4. tags
function orderedRefs(refs) {
  if (!refs || refs.length === 0) return [];
  const head = refs.find((r) => r.is_head && r.type === "branch");
  const detached = refs.find((r) => r.type === "head");
  const rest = refs.filter(
    (r) => r !== head && r !== detached && r.type !== "head",
  );
  const buckets = { branch: [], remote: [], tag: [] };
  for (const r of rest) if (buckets[r.type]) buckets[r.type].push(r);
  const ordered = [];
  if (head) ordered.push({ ...head, combinedWithHead: true });
  else if (detached) ordered.push(detached);
  ordered.push(...buckets.branch, ...buckets.remote, ...buckets.tag);
  return ordered;
}

// Type-prefix glyphs give an accessibility cue that doesn't rely on color
// (AC-6): the shape/character alone distinguishes the ref type for users
// with color-vision differences.
const REF_GLYPHS = {
  branch: "⎇",  // branch fork
  remote: "☁",  // cloud (remote)
  tag: "⚑",     // flag/pennant (tag)
  head: "◉",    // filled circle (HEAD pointer)
};

function refBadgeLabel(entry) {
  if (entry.type === "head") return "HEAD";
  if (entry.combinedWithHead) return `HEAD → ${truncateRefName(entry.name)}`;
  // Prefix tags with "tag:" — matches `git log --decorate` and gives a text
  // cue that branch vs tag no longer relies on the glyph rendering
  // correctly (AC-6 accessibility: some fonts render ⎇/⚑ as tofu).
  if (entry.type === "tag") return `tag: ${truncateRefName(entry.name)}`;
  return truncateRefName(entry.name);
}

function refBadgeClass(entry) {
  if (entry.type === "head" || entry.combinedWithHead) return "ref-badge ref-head";
  return `ref-badge ref-${entry.type}`;
}

// Render one row's badges starting at ``x``, return the width consumed
// (badges + trailing gap) so the caller can shift the subject to the right.
function renderRefBadges(svg, refs, xStart, y) {
  const ordered = orderedRefs(refs);
  if (ordered.length === 0) return 0;
  let x = xStart;
  for (const entry of ordered) {
    const label = refBadgeLabel(entry);
    const cls = refBadgeClass(entry);
    const glyph = REF_GLYPHS[entry.type] || "";
    const groupY = y - BADGE_H / 2;
    const g = el("g", { class: cls });
    const rect = el("rect", {
      class: "ref-badge-bg",
      x,
      y: groupY,
      height: BADGE_H,
      rx: 3,
      ry: 3,
    });
    g.appendChild(rect);
    const text = el(
      "text",
      {
        class: "ref-badge-label",
        x: x + BADGE_PAD_X,
        y,
        "dominant-baseline": "central",
      },
      `${glyph} ${label}`,
    );
    g.appendChild(text);
    // Full-text tooltip so a truncated badge still reveals its full ref name.
    g.appendChild(el("title", {}, `${entry.type}: ${entry.name}${entry.is_head ? " (HEAD)" : ""}`));
    svg.appendChild(g);
    // Measure after insertion (text is now in the layout tree) and size the
    // rect to fit; fall back to a character-based estimate if measurement is
    // unavailable (e.g. detached testing envs).
    let textWidth;
    try {
      textWidth = text.getComputedTextLength();
    } catch {
      textWidth = (`${glyph} ${label}`).length * 6.5;
    }
    const w = Math.max(textWidth + BADGE_PAD_X * 2, BADGE_H);
    rect.setAttribute("width", w);
    x += w + BADGE_GAP;
  }
  return x - xStart;
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
  // Provisional width; recomputed below once badge extent is known so the
  // meta column (right-anchored at ``width - 12``) never collides with the
  // shifted subject text.
  let width = Math.max(textX + 640, 900);
  const bottomY = height;

  const svg = el("svg", { width, height, viewBox: `0 0 ${width} ${height}` });
  // Attach the SVG to the DOM BEFORE rendering the per-row content: SPEC-004
  // badge sizing calls ``getComputedTextLength()`` to measure variable-width
  // ref names, and that only returns a real width once the text element is
  // in the layout tree. If we defer the attach to the end (SPEC-001's
  // original approach) every badge collapses to the fallback size and the
  // subject text overlaps the badges.
  graph.appendChild(svg);

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

  // SPEC-004: badges are anchored to each commit's lane node (labels-in-graph
  // layout — like gitk/GitLens-classic). Because badge widths vary by row,
  // the text column (sha/subject/meta) must shift right past the widest
  // badge extent across all rows so labels never collide with the text
  // column. Two passes:
  //   Pass 1 — render row hit-areas, nodes, and badges (measured in-DOM).
  //            Track maxBadgeRight = max over rows of (nodeX + badgeWidth).
  //   Pass 2 — render sha/subject/meta at shaX = max(textX, maxBadgeRight + gap).
  const badgeAnchorGap = LANE_W / 2 + NODE_R; // clearance from node
  let maxBadgeRight = 0;

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

    if (c.refs && c.refs.length) {
      const badgeStart = laneX(c.lane) + badgeAnchorGap;
      const badgesWidth = renderRefBadges(svg, c.refs, badgeStart, y);
      const rightEdge = badgeStart + badgesWidth;
      if (rightEdge > maxBadgeRight) maxBadgeRight = rightEdge;
    }
  });

  const shaX = Math.max(textX, maxBadgeRight + TEXT_GAP);
  const subjectX = shaX + 64;

  // Fit the SVG to the available viewport width (with a floor for very
  // narrow windows) so the subject column can breathe when there's room and
  // the meta column stays right-anchored without overlapping. Fall back to a
  // provisional width if the container hasn't laid out yet.
  const availableWidth = graph.clientWidth || document.documentElement.clientWidth || 900;
  const targetWidth = Math.max(availableWidth, subjectX + 320);
  if (targetWidth !== width) {
    width = targetWidth;
    svg.setAttribute("width", width);
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
    svg
      .querySelectorAll("rect.row-hit")
      .forEach((r) => r.setAttribute("width", width));
  }

  // Pass 2a — render the meta text (author · date, right-anchored) and
  // measure each row's width so we know how much space the subject has left
  // on each row. Take the max meta width to guarantee columnar alignment:
  // the subject is truncated to the same right-edge on every row.
  const metaRight = width - 12;
  const metaTexts = commits.map((c, i) => {
    const y = rowY(i);
    const node = el(
      "text",
      { class: "meta", x: metaRight, y, "dominant-baseline": "central", "text-anchor": "end" },
      `${c.author_name} · ${fmtDate(c.authored_timestamp)}`,
    );
    svg.appendChild(node);
    return node;
  });
  let maxMetaWidth = 0;
  for (const node of metaTexts) {
    let w = 0;
    try { w = node.getComputedTextLength(); } catch { w = 0; }
    if (w > maxMetaWidth) maxMetaWidth = w;
  }
  const subjectMaxWidth = Math.max(metaRight - maxMetaWidth - 24 - subjectX, 60);

  // Pass 2b — sha + subject text (truncated to the shared subjectMaxWidth
  // so no row overlaps the meta column).
  commits.forEach((c, i) => {
    const y = rowY(i);
    svg.appendChild(el("text", { class: "sha", x: shaX, y, "dominant-baseline": "central", fill: c.color }, c.short_sha));
    const subj = el(
      "text",
      { class: "subject", x: subjectX, y, "dominant-baseline": "central" },
      c.subject,
    );
    svg.appendChild(subj);
    // Full subject in a <title> so a truncated row still reveals its full
    // text on hover (mirrors the ref-badge tooltip pattern).
    let subjectWidth = 0;
    try { subjectWidth = subj.getComputedTextLength(); } catch { subjectWidth = 0; }
    if (subjectWidth > subjectMaxWidth) {
      // Character-based binary trim — cheap and good enough since the font
      // is proportional; add a tooltip so the untruncated text remains
      // discoverable.
      let s = c.subject;
      while (s.length > 1 && subj.getComputedTextLength() > subjectMaxWidth) {
        s = s.slice(0, -1);
        subj.textContent = s + "…";
      }
      subj.appendChild(el("title", {}, c.subject));
    }
  });
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
