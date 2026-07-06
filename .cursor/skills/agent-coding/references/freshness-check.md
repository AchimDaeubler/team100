# Freshness Check

Advisory freshness check invoked from `.cursor/skills/agent-coding/SKILL.md`
during spec validation, before any `in_progress` state write. Run this
when `meta.yaml.ready_sha` is present.

- If `ready_sha` is absent, skip this check silently. Older or manually created
  specs are allowed.
- Extract repo-root-relative paths from **Implementation guidance** -> **Files
  likely affected**. Support both inline backticked paths and one-path-per-line
  bullet formatting. Ignore prose that is not a repo file path.
- If no repo paths can be extracted, skip the path-limited diff. Do not diff
  the whole repository as a fallback.
- Validate `ready_sha` as a commit (for example with
  `git rev-parse --verify <sha>^{commit}`). If it is invalid or cannot be
  compared cleanly in the current repo state, do not fail execution. Treat that
  as a low-confidence freshness signal and recommend `full re-research` if the
  user wants a refresh before execution.
- Compare `ready_sha` to the current `HEAD` as two endpoints, limited to the
  watched paths (for example `git diff --name-only <ready_sha> HEAD -- <paths>`;
  do not use `...` merge-base diff semantics here). If any watched files
  differ, warn concisely before continuing: list the changed files and state
  that execution is still advisory rather than blocked.
- When you need to judge whether narrow scoping is trustworthy, inspect
  status-rich drift for the same watched paths (for example
  `git diff --name-status <ready_sha> HEAD -- <paths>`) so you can distinguish
  simple edits from renames, deletions, or broader config churn.
- Independently of file drift, use `meta.yaml.updated` as a coarse ready-age
  heuristic before Step 3 mutates it. If the spec has been in `ready` for more
  than 14 days, append a brief note that the research may warrant a quick
  re-check even if no watched files changed.
- If no file-drift, age-drift, or low-confidence comparison signal exists,
  continue directly to Step 2.
- If any freshness signal exists, pause before execution mode selection and
  present exactly these three choices:
  1. `proceed` — accept the advisory warning and continue toward execution
  2. `targeted re-research` — run a delta refresh scoped to the changed files
     and immediate context, plus any time-based external drift checks
  3. `full re-research` — rerun the full research gate before execution
- `[SIGNAL]` — execution cannot silently choose how to handle stale
  research.
- Recommend `targeted re-research` when the signal is narrow watched-file drift
  or age-based drift that still looks trustworthy to scope.
- Recommend `full re-research` when the baseline is invalid or non-comparable,
  or when rename / delete / config-style churn makes a narrow delta
  untrustworthy.
- If the user chooses `proceed`, continue to Step 2 with no spec edits.
- If the user chooses `targeted re-research`, keep the spec in `ready` and run
  this subflow before Step 2:
  1. Build a delta brief for the lanes:
     - spec `id`, `title`, and `category`
     - problem statement and relevant acceptance criteria
     - current `Research` and `Implementation guidance` findings, grouped by
       source section
     - watched paths, changed paths, and any rename / delete / config-style
       ambiguity you detected
     - baseline context: `ready_sha`, `meta.yaml.updated`, and whether the age
       signal crossed 14 days
  2. Read `research_subagents` from
     [`.spec/user-config.yaml`](user-profile.md) (absent or malformed →
     `true`). The toggle decides how the lanes run but not which
     lanes run or how findings are synthesized:
     - `research_subagents: true` → dispatch the selected lanes as parallel
       subagents.
     - `research_subagents: false` → the main agent performs the same lane
       investigations inline in a single pass, grouped by lane attribution.
  3. Run `repo-analyst` and `learnings-curator` on every targeted refresh.
  4. Run `docs-researcher` and `prior-art-researcher` only when the age
     signal or the changed surface suggests external drift is plausible.
  5. When a dispatched lane returns empty or whitespace-only output from
     `Await`, apply
     [subagent-dispatch.md](subagent-dispatch.md) to recover the lane's
     final message from its transcript before treating the lane as failed.
     A salvaged lane feeds synthesis with its attribution suffixed
     `(salvaged from transcript)` and counts as a successful lane for the
     "no meaningful delta" check below. Salvage does not apply to the
     inline path.
  6. Treat the lanes as evidence gatherers. The parent agent owns synthesis and
     approval-gated edits regardless of which path ran the lanes.
  7. If every invoked lane reports no meaningful delta, tell the user the
     research still stands, leave `spec.md` unchanged, and continue to Step 2.
  8. Otherwise, present a delta summary that distinguishes:
     - prior findings that still stand
     - findings that should be updated or removed
     - newly relevant findings to add
     - any refreshed `Files likely affected` or `Patterns to follow`
  9. Wait for explicit user approval before rewriting `spec.md`.
  10. If approved edits will touch the spec, create and check out the eventual
      `SPEC-*` feature branch first so the refresh lands on the feature branch,
      but do not set `status: in_progress` yet.
  11. Update only the stale or newly-added bullets inside the existing
      `## Research` and `## Implementation guidance` sections. Preserve
      still-valid bullets in place, and mark modified or appended bullets
      `updated via staleness re-research`.
  12. In this v1 flow, do not automatically refresh `ready_sha`. If the user
      stops after the refresh, repeat warnings on the same drift are expected
      until the spec is re-readied or otherwise re-baselined.
- If the user chooses `full re-research`, keep the spec in `ready`, reuse the
  [`research-gate.md`](../../create-spec/references/research-gate.md) pattern
  with full-surface inputs rather than changed-path scoping. That reference
  reads `research_subagents` itself, so the same toggle governs dispatch here
  — `true` dispatches the four lanes, `false` runs them inline. Wait for
  explicit approval before rewriting `spec.md`. If those approved edits mutate
  the spec, create the eventual `SPEC-*` feature branch first, but still
  defer `status: in_progress` until Step 3.
- Graceful degradation is independent of the toggle: a failed dispatch under
  `research_subagents: true` still falls back to inline coverage for that
  lane with a brief attribution note, exactly as the research gate prescribes.
