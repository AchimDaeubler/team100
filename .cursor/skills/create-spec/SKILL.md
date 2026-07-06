---
name: create-spec
description: >
  Create a spec — the unit of work in the Creator process. Scaffolds a spec
  directory with spec.md and meta.yaml, guides through required sections, and
  enforces the mandatory research gate. Use when the user asks to create a spec,
  plan work, write a PRD, define a task, or spec out a feature/bug/refactor.
---

# Create a Spec

A spec is a directory under `.spec/` containing two files: `spec.md` (what
we're building and why) and `meta.yaml` (lifecycle state and learnings). Every
unit of work — feature, bug fix, refactoring, or test coverage — starts as a
spec.

## Prerequisites

Apply [references/dependency-preflight.md](references/dependency-preflight.md)
before Step 1. Run all checks and present a consolidated report.

| Dependency | Type | Purpose |
|------------|------|---------|
| `git` | Required | Version control, branching, commits |
| `gh` | Optional | Remote ID allocation via ref claims (falls back to local-only scan) |
| Platform shell | Required | Script execution (next-id, scaffold, transition) |

If any required dependency is missing, stop with the error report. If `gh` is
missing, warn that ID allocation uses local-only scan and ask before proceeding.

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 1.
- Mode governs tag behavior and explanation depth. Does not relax research gate or decomposition rules.
- `[CHECK]` decomposition, blast radius. `[SIGNAL]` prior learnings, ready handoff. `[NOTE]` batch scaffolding.

## Workflow

Follow these steps in order. Do not skip the research gate.

### Step 1: Check whether the ask is one spec

Before choosing a category, decide whether the request should stay as a single
spec.

Treat the ask as too large when you see signals like:

- multiple phases or milestones
- multiple independently shippable subsystems
- roadmap language such as "what next?", "plan the next steps", or "phase 1/2/3"
- work that would naturally land as several PRs or need separate research
  threads

**IF** those signals appear — `[CHECK]`:

1. STOP before assigning a single spec ID or drafting one giant umbrella spec.
2. Decompose into a lightweight ordered backlog of spec candidates.
3. Keep each item spec-sized: title, category, one-sentence outcome, sequencing
   note.
4. Tell the user specs remain the unit of work; the backlog is a planning aid.
5. **IF** the user wants one slice now, **THEN** ask which slice. Recommend a
   fresh session.
6. **IF** the user wants multiple items scaffolded, **THEN** `[NOTE]` —
   read [references/batch-scaffolding.md](references/batch-scaffolding.md).
7. Only continue to Step 2 after one bounded slice is selected or batch
   scaffold requested.

### Step 2: Determine category

Ask the user (or infer from context) which category this spec is:

| Category | When to use |
|----------|-------------|
| **feature** | New capability, endpoint, UI, or behavior |
| **bug** | Something is broken and needs fixing |
| **refactoring** | Structural improvement with no behavior change |
| **testing** | Adding test coverage to existing code |

Default to `feature` if ambiguous. The user can change it.

### Step 3: Assign ID and create directory

1. Run `scripts/next-id.ps1` (PowerShell) or `scripts/next-id.sh` (bash/zsh)
   to get the next sequential spec ID.
2. Ask the user for a short title. Generate a slug from it (lowercase,
   hyphens, no special characters).
3. Resolve the owner: run `git config user.name` and use the output as the
   `<owner>` parameter. This is the single deterministic source — do not
   infer from GitHub usernames, context, or other sources.
4. Run `scripts/scaffold.ps1 <id> <slug> <category> <owner> [depends_on...]`
   (PowerShell) or `scripts/scaffold.sh <id> <slug> <category> <owner>
   [depends_on...]` (bash/zsh) to create the directory with populated
   `spec.md` and `meta.yaml`.
   - If batch scaffolding established sequencing, pass `depends_on` SPEC IDs
     as additional arguments.

### Step 4: Determine branch context

Apply `.cursor/rules/branch-state-reconciliation.mdc` first to decide
stay/swap/prompt/refuse-and-ask. Then, on whichever branch it lands:

- **On a `planning-*` or `SPEC-*` branch:** continue on it.
- **On the default branch**, branch by intent (always honor
  `branching.base_branch` from `meta.yaml` when present):
  - **Batch / "just planning":** create `planning-{slug}` from
    `origin/HEAD` (slug describes the theme).
  - **"Build now":** create `SPEC-{n}-{slug}` from
    `branching.base_branch` if set, else `origin/HEAD`. `agent-coding`
    continues on it without creating a new branch.

Branch creation: `git checkout -b <branch-name> <base>`.

### Step 5: Refine scaffolded files

The scaffold script creates both files from templates. Refine them:

**spec.md** — Update the frontmatter:
- Set `title` to the full human-readable title (the scaffold uses the slug)
- Confirm `authored_by` (`augmented` for interactive sessions, `automated` for
  agent-generated specs)

**meta.yaml** — If the user provides a source URL or tracking ID, add the
origin fields. Use a shareable URL/ID or a generic breadcrumb, never a local
filesystem path. Reserve `blocked_by` for cases where the user explicitly
needs a stronger advisory threshold.

### Step 6: Populate required sections

Work with the user to fill in the required sections. Every spec needs:

1. **Problem statement** — What problem, who is affected, why it matters.
   Must be understandable without external context.
2. **Acceptance criteria** — Numbered, testable. Each criterion describes an
   *observable outcome*, not an implementation step.
3. **Scope boundaries** — What is explicitly out of scope.

Then fill in category-specific required sections:
- **Bug**: Reproduction (exact inputs, wrong output, expected output)
- **Refactoring**: Current state, Target state, Behavioral equivalence
- **Testing**: Coverage targets

For a complete worked example matching this category, read the corresponding
example from `assets/examples/`.

### Step 7: Blast radius assessment

`[CHECK]` — assess the spec's blast radius and classify for parallel-work
coordination. The agent makes this call, not the user.

Read [references/blast-radius.md](references/blast-radius.md) and follow the
classification procedure. Evaluate the heuristic questions against the spec's
scope and the repo's current structure, record the classification in
`meta.yaml`, and deliver mode-aware guidance with reasoning.

### Step 8: Research gate

This is the most important step. Do not skip it.

Batch scaffolding exception: if Step 1 entered batch mode, stop before this
step for every generated spec. Tell the user research is deferred and each
scaffolded spec must come back through Steps 8 and 9 individually, typically in
dependency order.

Read [references/research-gate.md](references/research-gate.md) and follow the
research procedure.

### Step 9: Mark ready

`[SIGNAL]` — readiness confirmation with mode-aware auto-proceed.

1. Present a short structured summary of the research findings:
   - prior learnings to carry forward
   - key codebase patterns, files, or constraints that shape implementation
   - any open questions, assumptions, or notable risks
2. **Clean-signal criteria**: research completed with no open questions,
   unresolved concerns, or notable risks worth surfacing.
3. **When signal is clean** — auto-proceed: run
   `scripts/transition.ps1 <spec-directory> ready` (PowerShell) or
   `scripts/transition.sh <spec-directory> ready` (bash/zsh), then apply the
   `spec-dashboard` skill to refresh the spec dashboard. Commit and recommend
   starting execution in a fresh session. In guided mode this still blocks;
   in safe-auto it auto-proceeds; in expert it informs; in streamlined it is
   silent.
4. **When a concern is flagged** (open questions, unresolved risks, or
   assumptions needing validation) — escalate one level per the `[SIGNAL]`
   escalation rules. Ask whether the spec should be marked `ready` or whether
   concerns need resolution first. Do not infer readiness from silence,
   context, or ambiguous signals.
5. If the user gives feedback or responds with anything short of explicit
   approval:
   - address the feedback or answer the question
   - update the spec if the research findings changed
   - re-present the summary as needed and ask again
6. Do not set `ready_sha` earlier during research; it must reflect the approved
   `ready` checkpoint itself.

The spec is now ready for execution via `agent-coding`.

## What happens next

After a spec reaches `ready`, the rest of the Creator flow is:

- **Agent execution** — implement the spec via `agent-coding` (required)
- **PR review** — review agent-authored changes via `pr-review` (required)
- **Learning curation** — run `spec-retro` after completion (default next step,
  unless explicitly deferred)

Spec files (`spec.md`, `meta.yaml`) are committed on whichever branch
`create-spec` established in Step 4 — a `planning-*` branch for batch/planning
workflows, or a `SPEC-*` branch for build-now workflows. When `agent-coding`
picks up the spec, it continues on the existing `SPEC-*` branch rather than
creating a new one. For the rest of the lifecycle, see
[references/lifecycle.md](references/lifecycle.md).

If you decomposed a broad request into backlog items without batch scaffolding,
stop here and let the next conversation pick one bounded item to turn into a
real spec. If you batch-scaffolded multiple drafts, push the `planning-*`
branch and open a PR, then stop here and research them one at a time in later
sessions, usually following any `depends_on` ordering.

## Gotchas

- NEVER skip the research gate — agents build redundant mechanisms when existing patterns exist undiscovered.
- NEVER write ACs like "implement the feature" — each criterion must describe a testable, observable outcome with specific values or behaviors.
- ALWAYS use repo-root-relative file paths in implementation guidance — vague guidance produces poor results. NEVER commit machine-specific paths (`/home/...`, `/Users/...`).
- IF the request spans multiple phases or subsystems, THEN decompose into a backlog before creating a spec.
- IF a spec's ID collides with another after offline allocation, THEN renumber via [references/renumbering.md](references/renumbering.md).
- ALWAYS include "Files NOT to modify" — agents refactor adjacent code if not explicitly told not to.
- NEVER treat `spec.md` as frozen — it evolves during execution. Capture discoveries as learnings in `meta.yaml`.

## When NOT to use this skill

- Executing code against an existing spec → `agent-coding` skill
- Reviewing an agent-authored PR → `pr-review` skill
- Curating learnings across specs → `spec-retro` skill
- Setting up a new repo for the Creator process → `repo-setup` skill
- Re-scoping a spec after review feedback (come back here with the
  existing spec directory; do not create a new one)

## Reference

For full field definitions, format details, or advanced lifecycle states, read
these files on demand:

- [references/spec-format.md](references/spec-format.md) — Complete field
  definitions for spec.md frontmatter, body sections, meta.yaml fields, and
  learning types
- [references/lifecycle.md](references/lifecycle.md) — Status transitions,
  gate rules, and branch conventions
- [references/user-profile.md](references/user-profile.md) — Optional local user
  profile schema, mode definitions, and tag behavior
