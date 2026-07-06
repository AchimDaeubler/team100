---
name: agent-coding
description: >
  Execute a spec via unsupervised or co-coding mode. Validates the spec is
  ready, transitions through in_progress, manages mandatory stop points, and
  completes the lifecycle with learnings and PR links. Use when the user says
  "execute this spec", "code this spec", or "implement this spec".
---

# Agent Coding

Execute a `ready` spec through the `in_progress` phase to `done`. Two modes:
**unsupervised** (autonomous, agent-driven) and **co-coding** (iterative,
human-driven). Both start with a spec and produce a PR.

## Prerequisites

Apply [references/dependency-preflight.md](references/dependency-preflight.md)
before Step 1. Run all checks and present a consolidated report.

| Dependency | Type | Purpose |
|------------|------|---------|
| `git` | Required | Version control, branching, commits |
| `gh` | Required | PR creation in completion workflow |
| Platform shell | Required | Script execution (transition, freshness-diff, capture-pr) |

If any required dependency is missing, stop with the error report before
doing any work.

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 1. Profile mode ≠ execution mode.
- Mode governs tag behavior, git visibility, and explanation depth.
- `[STOP]` draft/terminal/mandatory stops, non-trivial conflicts. `[CHECK]` in_progress resume, simple conflicts. `[SIGNAL]` exec mode, freshness, AC verify (unsupervised), self-review auto-chain, retro auto-chain. `[GATE]` freshness rewrite, AC verify (co-coding). `[NOTE]` git ops, trivial rebase.

## Workflow

Follow these steps in order.

### Step 1: Validate the spec

Read the spec's `meta.yaml` and check `status`:

- **IF `ready`:** Proceed.
- **IF `draft` or `research`:** `[STOP]` — spec must reach `ready`. Point to
  `create-spec`.
- **IF `in_progress`:** `[CHECK]` — ask whether to resume or restart.
- **IF `done` or `cancelled`:** `[STOP]` — terminal state.

**IF `meta.yaml` includes dependency fields:**

- `depends_on`: read each upstream `meta.yaml`.
  - IF any missing or not `done`, THEN warn concisely but continue.
- `blocked_by`: read each upstream `meta.yaml`.
  - IF any missing or below `until_status`, THEN warn but continue.
  - `until_status: ready` satisfied by `ready | in_progress | blocked | done`.
  - `until_status: done` satisfied only by `done`.
- Keep warnings concise: name, current status, advisory not blocking.

Read `spec.md` fully. Confirm you understand the acceptance criteria, scope
boundaries, and implementation guidance before continuing.

If `meta.yaml.ready_sha` is present, run
`scripts/freshness-diff.ps1 <spec-directory>` (PowerShell) or
`scripts/freshness-diff.sh <spec-directory>` (bash/zsh) to check for file
drift against `ready_sha`. If the script reports changed files, read
[references/freshness-check.md](references/freshness-check.md) for the
advisory freshness procedure before proceeding to Step 2. Use the
`--name-status` flag when you need to distinguish renames, deletions, or
config churn from simple edits.

### Step 2: Select execution mode

`[SIGNAL]` — ask the user which mode to use:

| Mode | Best for |
|------|----------|
| **Unsupervised** | Well-specified ACs, clear file paths, testable outcomes, taste is not a factor |
| **Co-coding** | UX/design-heavy, taste matters, exploratory implementation, learning-oriented |

If unsure, recommend **unsupervised** when ACs are concrete and testable,
**co-coding** when outcomes require human judgment to evaluate.

User profile mode may change how much explanation or confirmation you give
here, but it does not choose the execution mode for you.

### Step 3: Prepare workspace and transition to in_progress

Apply `.cursor/rules/branch-state-reconciliation.mdc` before the
spec-branch match below, so a stale merged branch lands on default first.
Then, on the reconciled branch:

- **Matches `SPEC-{n}-*` for this spec:** continue on it.
- **Otherwise:** `git checkout -b SPEC-{n}-{slug} <base>`, where `<base>`
  is `branching.base_branch` from `meta.yaml` if set, else `origin/HEAD`.
- **Parallel execution:** `git worktree add` keeps default clean — avoid on
  WSL/Windows unless known to work.

Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory>
in_progress` (PowerShell) or `.cursor/skills/create-spec/scripts/transition.sh
<spec-directory> in_progress` (bash/zsh) on the feature branch to set the
status and update the date, then apply the `spec-dashboard` skill to refresh
the spec dashboard.

After transitioning, refresh the owner if needed: run `git config user.name`
and compare with the `owner:` line in `spec.md`. If they differ, replace the
`owner:` line with the implementer's name using targeted string replacement
(PowerShell `-replace` on `^owner:.*` or `sed` equivalent). This transfers
accountability from the spec creator to the implementer.

NEVER do this until Step 1 advisories have been surfaced and any re-research
path is complete. ALWAYS do this BEFORE writing any implementation code.

### Step 4: Load context

Read these files to build execution context:

1. The spec's `spec.md` — ACs, scope boundaries, implementation guidance
2. The spec's `meta.yaml` — any existing learnings from prior attempts
3. Files listed in **Implementation guidance** → "Files likely affected"
4. Files listed as patterns to follow
5. Repo rules in `.cursor/rules/` if they exist

- Before writing, search the relevant area for existing sections, patterns,
  utilities, and abstractions you can reuse or extend.
- Prefer refining existing skills, docs, or code over additive growth. Do not
  add parallel wrappers or boilerplate when extending an existing pattern will
  do the job, and tighten or remove superseded wording instead of leaving
  parallel structure behind.

Do NOT read files under "Files NOT to modify" unless needed to understand an
interface boundary.

---

### Steps 5–7: Execute in the selected mode

- **Unsupervised**: Read
  [references/unsupervised-mode.md](references/unsupervised-mode.md) and follow
  Steps 5a–7a.
- **Co-coding**: Read
  [references/co-coding-mode.md](references/co-coding-mode.md) and follow
  Steps 5b–7b.

---

### Step 8: Complete the spec (both modes)

When all ACs are verified, read
[references/completion-workflow.md](references/completion-workflow.md) and
follow the completion procedure.

### Steps 9–10: Handle blocked or cancelled (when needed)

If execution cannot continue or the user abandons the spec, read
[references/blocked-cancelled.md](references/blocked-cancelled.md).

## Gotchas

- NEVER rely on passive "consider splitting" — agents do not self-correct. Mandatory stop points are the only reliable mechanism.
- NEVER skip a stop point — when a stop condition triggers, you MUST stop and present options.
- IF within-scope clarification, polish, or small follow-up, THEN keep moving — clean breaks are for unit-of-work scope changes, not tiny fixes.
- ALWAYS update `spec.md` when new information emerges during execution — git history preserves the baseline.
- ALWAYS capture learnings in `meta.yaml` as they emerge — do not wait for Step 8.
- IF baseline is invalid, rename/delete churn appears, or config changes make impact ambiguous, THEN recommend `full re-research` over targeted.
- NEVER assume targeted refresh re-baselines `ready_sha` — the same staleness warning may recur until re-readied.
- ALWAYS demand specific file paths in implementation guidance — vague guidance produces vague results.
- NEVER stretch one chat across multiple specs — prefer a fresh session after `done`, `blocked`, or `cancelled`.

## When NOT to use this skill

- Creating or researching a spec → `create-spec` skill
- Reviewing an agent-authored PR → `pr-review` skill
- Setting up a new repo → `repo-setup` skill
- Curating learnings across specs → `spec-retro` skill

## Reference

For lifecycle transitions and field definitions, read these on demand:

- [references/lifecycle.md](references/lifecycle.md) — Status transitions,
  gate rules, and completion workflow
- [references/spec-format.md](references/spec-format.md) — Field definitions
  for spec.md and meta.yaml
- [references/user-profile.md](references/user-profile.md) — Optional local user
  profile schema, mode definitions, and tag behavior
