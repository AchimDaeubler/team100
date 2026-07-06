# Dimension Review — Dispatch Path

Applied from `.cursor/skills/pr-review/SKILL.md` **Step 3A**. Mirrors the
parallel-lane-then-synthesize procedure documented in
`.cursor/skills/create-spec/references/research-gate.md` (steps 3–6 of
that reference — refer to it by path, not by step number, because
`create-spec/SKILL.md` has since renumbered its callers).

## 1. Build the shared review brief

Assemble one brief that every lane receives, then extend it per lane
with the lane-specific checklist rows below. The brief contains:

- Spec identity: `id`, `title`, `category`
- The spec's full `spec.md` and `meta.yaml`
- The PR diff, with added / modified / deleted paths clearly listed
- Whether this is self-review (local branch diff) or open-PR review

## 2. Extend the brief per lane

For each lane, append exactly the Dimension N signal rows from
`.cursor/skills/pr-review/assets/review-checklist.md` — the **checklist
is the single source of truth**; do not paraphrase. A lane must never
receive rows from another dimension.

| Lane | Checklist rows to include |
|------|---------------------------|
| `spec-compliance-reviewer` | Dimension 1 rows (AC coverage, verification fidelity, completeness) |
| `scope-drift-reviewer` | Dimension 2 rows (file, functional, dependency boundaries) |
| `test-coverage-reviewer` | Dimension 3 rows (new behavior, regressions, edge cases) and the `☐ N/A (non-code spec)` option |
| `security-surface-reviewer` | Dimension 4 rows (secrets, input handling, permissions) and the `☐ N/A (non-code spec)` option |
| `approach-quality-reviewer` | Dimension 5 rows (pattern conformance, simplicity, readability, skill file size) |

Also tell each lane which dimensions it must **not** evaluate and point
concerns to the owning lane — this mirrors the "How you differ from the
other review lanes" text already in each agent file and prevents lane
bleed at dispatch time.

## 3. Dispatch the five lanes in parallel

Launch all five in a single message (one `Task` call per lane). Cursor's
subagent runtime starts each with a clean context, so the full brief
plus the lane-specific extension must be injected in the prompt — do
not rely on inherited context.

Each lane declares `model: inherit`, `readonly: true`,
`is_background: true` in its agent file; no per-dispatch override is
needed.

## 4. Handle per-lane failure gracefully

If a lane fails to launch, errors mid-run, or returns a malformed
report, recover by evaluating **only that dimension** using the inline
signal walk in
[dimension-review-inline.md](dimension-review-inline.md). The other
four dimensions keep their dispatch results. The review never blocks on
a subagent failure (AC-7). Note the fallback explicitly in the verdict
so the reader knows which dimension was covered inline.

### 4a. Salvage before declaring a lane failed

Before treating an empty or whitespace-only lane return as a failure,
apply [subagent-dispatch.md](subagent-dispatch.md) to recover the
lane's final message from its transcript. A salvaged lane is handed to
Step 5 synthesis as a clean return with its attribution suffixed
`(salvaged from transcript)`, and it counts as a **successful** lane
for the ≥2-lane-failure threshold below. Only lanes that fail salvage
count toward that threshold, and only those lanes need the inline
dimension walk.

If two or more lanes fail in the same run, prefer the full inline path
(Step 3B in `SKILL.md`) rather than reconstructing dispatch piecemeal —
the inline path is factored to produce the same verdict shape.

## 5. Treat lane output as evidence, not verdict

Each lane returns `Status`, `Summary`, severity-tagged `Findings`, and
optional `Open questions / risks` / `Fallback note`. These are inputs
to synthesis, not the final per-dimension verdict. The main agent:

- deduplicates cross-lane findings (one bullet, both lanes attributed,
  severity normalized)
- re-ranks severity using a single arbitration policy rather than
  averaging per-lane rankings
- reconciles any `N/A` determinations against the actual diff content
- maps severity to the unchanged Step 5 verdict shape:
  `blocking` → dimension `fail`, `advisory` → dimension `flag`, no
  findings → dimension `pass`
- hands the synthesized per-dimension verdict to Step 4 anti-gaming

Synthesis happens in `SKILL.md` Step 3 after both paths converge, so
Step 4 anti-gaming and Step 5 verdict remain dispatch-agnostic.
