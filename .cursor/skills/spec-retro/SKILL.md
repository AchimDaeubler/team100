---
name: spec-retro
description: >
  Curate learnings from completed specs. Evaluates quality, identifies
  cross-spec patterns, promotes high-value insights to the ledger and repo
  knowledge, and flags stale entries. Use when the user says "retro this spec",
  "curate learnings", or "review learnings".
---

# Spec Retro

Curate raw learnings from `done` specs into reusable knowledge. Two modes:
**single-spec retro** (just-completed spec) and **multi-spec sweep** (periodic
cross-spec review). Single-spec retro is the default next action after
`agent-coding` completes a spec.

## Prerequisites

Apply [references/dependency-preflight.md](references/dependency-preflight.md)
before Step 1. Run all checks and present a consolidated report.

| Dependency | Type | Purpose |
|------------|------|---------|
| `git` | Required | Branch operations, commits, ledger updates |

If `git` is missing, stop with the error report.

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 1.
- Mode governs tag behavior and explanation depth.
- `[CHECK]` retro mode, docs pass. `[SIGNAL]` meta improvements, learning improvements, ledger curation, promotion. `[GATE]` rebuild replacements. `[STOP]` spec not done.

## Workflow

### Step 1: Select retro mode

When arriving from an `agent-coding` completion auto-chain (same session,
spec just reached `done`), auto-select **single-spec retro** and skip the
`[CHECK]` prompt below — the mode is already determined by the auto-chain.

Otherwise, `[CHECK]` — ask the user which mode to use:

| Mode | Best for |
|------|----------|
| **Single-spec retro** | Just completed a spec — evaluate and curate its learnings |
| **Multi-spec sweep** | Periodic review — find cross-cutting patterns, duplicates, contradictions |

Recommend single-spec immediately after completion or when resuming a deferred
completion handoff; multi-spec when several specs have completed since the last
sweep or the user explicitly wants ledger-wide curation or rebuild work.

### Step 2: Establish branch context and gather learnings

**Branch context — single-spec retro:**

- **Auto-chained from completion** (same session): you are already on the
  `SPEC-*` implementation branch. Stay on it. All retro commits (ledger,
  rules, docs promotions) land on this branch and appear on the open PR.
- **Standalone invocation, branch still exists:** check out the implementation
  branch (`SPEC-{n}-*`) before committing retro outputs.
- **Deferred invocation, branch no longer exists** (PR already merged/deleted):
  create a `retro-SPEC-{n}` branch from `origin/HEAD` for promotion commits.
  Push and open a PR after curation completes.

**Branch context — multi-spec sweep:** Create a `retro-{slug}` branch from
`origin/HEAD` (e.g., `retro-april-sweep`). All sweep curation commits land on
this branch. Push and open a PR after all curation steps complete.

**Gathering learnings — single-spec:** If arriving from an `agent-coding`
completion auto-chain in the same session, the completion context (spec
identity, `status: done`, PR URLs, raw learnings) is already loaded — skip
re-reading `meta.yaml` and `spec.md`. Still load `.spec/_ledger/` if it exists
so you can tell whether a strong learning should become a new ledger entry,
refine an existing one, or stay spec-local for now.

Otherwise (standalone invocation or deferred handoff), read the target spec's
`meta.yaml`. Verify `status: done`. If the user arrives from a deferred
completion handoff, use that handoff as starting context, but still confirm the
completion state, PR URLs, and raw learnings from `meta.yaml`. If the spec is
not `done`, STOP — learnings should be curated after execution completes. Also
read `spec.md` for context on what the spec accomplished. Load
`.spec/_ledger/` too.

**Gathering learnings — multi-spec sweep:** Scan `.spec/` for directories
where `meta.yaml` has `status: done`. Collect all learnings from each. Also
load the existing ledger from `.spec/_ledger/` if it exists. Treat existing
ledger entries as curation targets, not just a duplicate check: you may refine
wording/context, normalize tags, merge overlap, or flag stale/contradicted
entries while reviewing new learnings.

---

### Steps 3–5: Evaluate in the selected mode

- **Single-spec retro**: Read
  [references/single-spec-retro.md](references/single-spec-retro.md) and follow
  Steps 3a–5a.
- **Multi-spec sweep**: Read
  [references/multi-spec-sweep.md](references/multi-spec-sweep.md) and follow
  Steps 3b–5c.

---

### Steps 6–7: Apply curation and retention review

Read [references/curation-workflow.md](references/curation-workflow.md) and
follow Steps 6–7. These apply in both single-spec and multi-spec modes. After
curation commits are complete, apply the `spec-dashboard` skill to refresh
the spec dashboard.

## Gotchas

- ALWAYS make curation output valuable — surface contradictions, duplicates, and cross-spec patterns rather than just "you should curate."
- ALWAYS treat existing ledger entries as curation targets — refine wording, normalize tags, merge overlap, mark stale entries.
- NEVER invent parallel retro artifacts from the completion handoff — validate against `spec.md` and `meta.yaml`.
- NEVER treat the ledger as precious — it carries `source_spec` traceability and can be rebuilt from `done` specs via explicit human-reviewed request.
- NEVER conflate agent-facing and human-facing knowledge — the ledger is for agents; README and docs are for humans. Check both surfaces.
- NEVER pre-create empty domain files — wait for enough learnings to accumulate before splitting a domain.
- NEVER enforce a tag taxonomy — normalize inconsistencies (e.g., `git-worktree` vs `worktree`) but do not impose a controlled vocabulary.

## When NOT to use this skill

- Creating or researching a spec → `create-spec` skill
- Executing a spec → `agent-coding` skill
- Reviewing an agent-authored PR → `pr-review` skill
- Setting up a new repo → `repo-setup` skill

## Reference

- [references/lifecycle.md](references/lifecycle.md) — Status transitions,
  gate rules, and completion workflow
- [references/spec-format.md](references/spec-format.md) — Field definitions
  for spec.md and meta.yaml (including learning types)
- [references/user-profile.md](references/user-profile.md) — Optional local user
  profile schema, mode definitions, and tag behavior
