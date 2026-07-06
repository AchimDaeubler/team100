---
name: pr-review
description: >
  Review agent-authored changes against their spec. Evaluates five dimensions
  (spec compliance, scope drift, test coverage, security surface, approach
  quality), applies anti-gaming checks, and reaches a structured verdict.
  Use when the user says "review this PR", "review my changes", "self review",
  "check before I push", or "is this ready to merge".
---

# PR Review

Review agent-authored changes by evaluating them against the originating spec.
Works in two modes: **self-review** (local changes before push) and **PR
review** (open pull request). Both produce a structured verdict: **approve**,
**request changes**, or **reject**. All PRs get human review in boot camp
v0 — no auto-merge, no risk-tier sampling.

## Prerequisites

Apply [references/dependency-preflight.md](references/dependency-preflight.md)
before Step 1. Run all checks and present a consolidated report.

| Dependency | Type | Purpose |
|------------|------|---------|
| `git` | Required | Diff generation, branch operations |

If `git` is missing, stop with the error report.

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 1.
- Mode governs tag behavior and explanation depth. Does not weaken review, anti-gaming, or merge safeguards.
- `[STOP]` no spec. `[GATE]` review verdict. `[SIGNAL]` post-approval follow-through. `[NOTE]` git follow-through.

## Workflow

Follow these steps in order.

### Step 1: Locate the spec

Identify the spec these changes implement. Check:

1. The PR title (`SPEC-<n>: <title>`)
2. The branch name (`SPEC-{n}-*`)
3. The PR description or commit messages for a spec reference
4. Changes to files under `.spec/`

Read the spec's `spec.md` and `meta.yaml` fully before reviewing any code.
**IF** no spec can be identified — `[STOP]`: unspecified work cannot be
reviewed against this framework.

### Step 2: Gather the diff

Determine the review mode and gather the diff accordingly:

- **Self-review** (no PR yet — local branch changes): run
  `git diff <default-branch>...HEAD` to get the full diff of changes on the
  current branch. Also check for uncommitted changes with `git diff`.
- **PR review** (open pull request): read the full PR diff.

In either mode, identify:

- Which files were added, modified, or deleted
- Which files appear in the spec's "Files likely affected" list
- Which files appear in the spec's "Files NOT to modify" list
- Any files changed that the spec does not mention at all

### Step 3: Evaluate the five review dimensions

Record a **pass**, **flag**, or **fail** per dimension against the
signal rows in
[assets/review-checklist.md](assets/review-checklist.md) — the
checklist is the single source of truth for signal wording.

Two paths produce the same verdict shape. Pick via the **path selector**
below, then synthesize per the shared synthesis subsection.

**Path selector** — read `review_subagents` from
[`references/user-profile.md`](references/user-profile.md) (absent or
malformed → `true`):

- `review_subagents: true` → **Step 3A (dispatch)** for the full
  dimension pass. Fall back to Step 3B (inline) for any dimension whose
  subagent fails or reports malformed output — other dimensions keep
  their dispatch results. Two or more lane failures in one run switch
  the whole pass to 3B.
- `review_subagents: false` → route the entire dimension pass directly
  to **Step 3B (inline)**; do not dispatch subagents. This is the opt-out
  hook called out in
  [`references/dimension-review-inline.md`](references/dimension-review-inline.md);
  the inline path is factored specifically so this is a pure route
  change, not a restructure.

The toggle is the user's explicit preference; the per-lane failure
fallback above is automatic and orthogonal — it still applies under
`review_subagents: true` exactly as before.

#### Step 3A — Dispatch path

Dispatch five parallel review-lane subagents (one per dimension):
`spec-compliance-reviewer`, `scope-drift-reviewer`,
`test-coverage-reviewer`, `security-surface-reviewer`,
`approach-quality-reviewer`. Each receives the shared brief plus the
exact checklist rows for its dimension, and returns a structured
result with severity-tagged findings (`blocking` / `advisory`).

Apply [references/dimension-review-dispatch.md](references/dimension-review-dispatch.md)
for the full brief shape, per-lane input contract, and per-lane
failure recovery procedure.

#### Step 3B — Inline path

The main agent walks the five dimension signal tables directly. Use it
when Step 3A cannot run end-to-end, for the per-lane fallback above,
or when a future gate on the path selector routes the whole pass here.

Apply [references/dimension-review-inline.md](references/dimension-review-inline.md)
for the five dimension tables and the same severity mapping.

#### Synthesis (both paths)

"Synthesize holistically across dimensions" takes priority over any
per-lane report shape verbatim. The main agent owns four synthesis
responsibilities before handing results to Step 4:

1. **Deduplicate** cross-lane findings — one bullet, every contributing
   lane attributed, severity normalized.
2. **Re-rank severity** using a single arbitration policy, not an
   average of per-lane rankings.
3. **Reconcile N/A** determinations against actual diff content — if a
   lane returned `N/A` but the diff contains evaluable content, override
   and evaluate.
4. **Hand the synthesized per-dimension verdict to Step 4** — anti-gaming
   runs after synthesis and before Step 5.

Severity mapping (applied once, at synthesis):

| Reviewer finding | Dimension verdict |
|------------------|-------------------|
| any `blocking` | `fail` |
| only `advisory` | `flag` |
| none | `pass` |

Note dispatch-path fallbacks explicitly in the per-dimension evidence
so readers see which dimensions were covered inline.

### Step 4: Anti-gaming checks

Agent-authored code requires explicit checks for these known failure
patterns. Flag any that appear:

1. **Measurement redefinition** — The agent changed how an AC is verified
   rather than meeting the AC as written. *Example: AC says "endpoint
   returns 400 on invalid input" and the agent changed the validation
   schema so the input is no longer invalid.*
2. **Proxy evidence** — The agent cites indirect evidence instead of
   demonstrating the outcome. *Example: "tests pass" as evidence for an
   AC about user-visible behavior, when the tests don't exercise that
   behavior.*
3. **Scope dismissal** — The agent marked a failing concern as "out of
   scope" when the spec does not exclude it. *Example: error handling
   declared out of scope when the spec's ACs include error cases.*
4. **Tautological tests** — Tests that cannot fail because they assert
   on the implementation's own output rather than expected values.
   *Example: `assert result == function_under_test(input)` — this always
   passes.*
5. **Silent AC omission** — One or more ACs have no corresponding change
   and no waiver. The agent simply didn't do them and didn't mention it.

### Step 5: Reach a verdict

`[GATE]` — the review verdict requires explicit presentation and acknowledgment.

Use the dimension results to determine the outcome:

| Verdict | Criteria |
|---------|----------|
| **Approve** | All dimensions pass (flags acceptable with explanation). No anti-gaming triggers. |
| **Request changes** | One or more dimensions flagged or failed, but the approach is sound. Provide structured feedback per dimension with specific file/line references. |
| **Reject** | Fundamental approach problem, anti-gaming trigger confirmed, or spec compliance failures that require rearchitecting. State the rationale and whether the spec itself needs revision. |

Present the verdict with:
1. A summary line (verdict + one-sentence rationale)
2. Per-dimension results (pass/flag/fail with evidence)
3. Anti-gaming check results (clean or triggered, with specifics)
4. Action items (for request-changes or reject)

### Step 6: After approval

`[SIGNAL]` — post-approval follow-through. `[NOTE]` — git operations.

**Self-review approved:** The changes are ready to push. Proceed with
creating the PR — invoke this skill again on the PR if a second review is
desired.

**PR review approved and merged:**

1. Verify `meta.yaml` is updated per the completion workflow in
   [references/lifecycle.md](references/lifecycle.md):
   - `status: done`, `updated` date set
   - `completion.date` and `completion.pull_requests` populated
   - Any waived ACs recorded with rationale
   - Learnings captured
2. If the spec's `meta.yaml` wasn't updated in the PR, remind the
   implementer to complete it before merging.

## Gotchas

- NEVER accept "tests pass" as a review — the five dimensions exist to catch what CI cannot.
- ALWAYS check anti-gaming patterns explicitly — agents redefine measurements, use proxy evidence, and dismiss errors as out of scope.
- ALWAYS check file boundaries first — scope drift (modifying files outside the spec) is the most common agent failure mode.
- IF the spec's ACs are vague or untestable, THEN reject and improve the spec — do not approve code that satisfies bad criteria.
- ALWAYS flag SKILL.md files that have grown past 250 lines — skill-size regression degrades instruction-following fidelity; request extraction to `references/` per `.cursor/rules/skill-authoring.mdc`.

## When NOT to use this skill

- Creating or researching a spec → `create-spec` skill
- Executing a spec → `agent-coding` skill
- Setting up a new repo → `repo-setup` skill
- Curating learnings across specs → `spec-retro` skill

## Reference

For dispatch / inline path details, lifecycle transitions, and
completion workflow, read these on demand:

- [references/dimension-review-dispatch.md](references/dimension-review-dispatch.md) —
  Shared-brief shape, per-lane input contract, and per-lane failure
  recovery for Step 3A
- [references/dimension-review-inline.md](references/dimension-review-inline.md) —
  The five dimension signal tables for Step 3B and per-lane fallback
- [references/lifecycle.md](references/lifecycle.md) — Status transitions,
  gate rules, and completion workflow
- [references/spec-format.md](references/spec-format.md) — Field
  definitions for spec.md and meta.yaml
- [references/user-profile.md](references/user-profile.md) — Optional local user
  profile schema, mode definitions, and tag behavior
