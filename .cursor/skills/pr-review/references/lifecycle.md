<!-- Shared reference: canonical source is `.cursor/skills/_shared/lifecycle.md`. Edit there, then run `./sync.sh`; do not hand-edit copied `references/` files. -->

# Spec Lifecycle

Status transitions, rules, and gate criteria. For field definitions, see spec-format.md.

## Status flow

```
              ┌───────────────────────────────┐
              │                               │
              ▼                               │
draft ──► research ──► ready ──► in_progress ──► done
                                    ▲
                                    │
                                    ▼
                                 blocked

Any non-terminal state ──► cancelled
```

## Statuses

| Status | Meaning | Entry conditions |
|--------|---------|------------------|
| `draft` | Spec exists but is incomplete | Created by any method |
| `research` | Content written; codebase investigation in progress | All required sections populated |
| `ready` | Approved for agent execution | Research complete. Owner sets status. |
| `in_progress` | Agent actively working | Assigned to agent or active co-coding |
| `blocked` | Paused — external dependency | Explicit block identified |
| `done` | Work complete, all ACs met or explicitly waived | All ACs met or waived with rationale |
| `cancelled` | Work will not be done | Explicit stop decision |

## Gate rules

> **Datestamp policy:** dates in `meta.yaml` must come from the local system
> clock via scripts — agents must never write a date literal. See
> [datestamp-policy.md](datestamp-policy.md) for the full rule.

### draft → research

- Problem statement is written
- Acceptance criteria are defined
- Scope boundaries are set
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> research` (PowerShell) or `transition.sh <spec-directory> research` (bash/zsh) to set `status` and `updated`, then apply the `spec-dashboard` skill to refresh the spec dashboard

### research → ready (THE MANDATORY GATE)

This is the most important transition. A spec CANNOT reach `ready` without codebase investigation.

Required before transitioning:
- Research section populated with concrete findings (file paths, pattern names, API behaviors)
- Implementation guidance populated with specific file paths and patterns
- Owner has reviewed and is satisfied the research is sufficient
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> ready` (PowerShell) or `transition.sh <spec-directory> ready` (bash/zsh) to set `status` and `updated`, then apply the `spec-dashboard` skill to refresh the spec dashboard

Evidence basis: specs defined without codebase research produced the worst agent outcomes. In the clearest case, an agent built a complex mechanism when the codebase already had a simple established pattern.

### ready → in_progress

- Spec assigned to an agent (unsupervised mode) or active co-coding session started
- If advisory dependency metadata (`depends_on` / `blocked_by`) is not yet
  satisfied, surface a warning before execution continues; do not block the
  transition
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> in_progress` (PowerShell) or `transition.sh <spec-directory> in_progress` (bash/zsh) to set `status` and `updated`, then apply the `spec-dashboard` skill to refresh the spec dashboard

### in_progress → done

- All acceptance criteria met (or explicitly waived with rationale)
- PR(s) opened and linked
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> done` (PowerShell) or `transition.sh <spec-directory> done` (bash/zsh) to set `status` and `updated`. Then populate the `completion` block manually. Apply the `spec-dashboard` skill to refresh the spec dashboard afterward
- Record any learnings discovered during execution
- In expert, streamlined, and safe-auto (clean signal) modes, auto-chain into
  single-spec retro using the completed spec identity, completion state, PR
  URLs currently known, and raw learnings from `meta.yaml`. In guided mode
  (or safe-auto with a concern), present the retro handoff and ask whether to
  run retro now or defer.

### in_progress → blocked

- External dependency identified that prevents progress
- Document the blocker (add a learning of type `constraint_found` or `decision_made`)
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> blocked` (PowerShell) or `transition.sh <spec-directory> blocked` (bash/zsh) to set `status` and `updated`, then apply the `spec-dashboard` skill to refresh the spec dashboard

### blocked → in_progress

- Blocker resolved
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> in_progress` (PowerShell) or `transition.sh <spec-directory> in_progress` (bash/zsh) to set `status` and `updated`, then apply the `spec-dashboard` skill to refresh the spec dashboard

### Any → cancelled

- Explicit decision to stop work
- Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> cancelled` (PowerShell) or `transition.sh <spec-directory> cancelled` (bash/zsh) to set `status` and `updated`, then apply the `spec-dashboard` skill to refresh the spec dashboard
- Optionally add a learning capturing why

## Completing a spec

When execution finishes and all acceptance criteria are met (or explicitly
waived), update `meta.yaml`:

1. Set `status: done`
2. Populate `completion.date`; leave `completion.pull_requests: []` for the
   `spec-retro` auto-chain to record (retro owns the PR URL write — see
   `.cursor/skills/spec-retro/references/single-spec-retro.md` Step 4a)
3. If any acceptance criteria were waived, list them with rationale in
   `acceptance_criteria_waived`
4. Add learnings for anything discovered during execution
5. `[SIGNAL]` retro auto-chain: in expert, streamlined, and safe-auto (clean
   signal) modes, invoke `spec-retro` in single-spec mode using the completed
   spec identity, completion state, and raw learnings. In guided mode (or
   safe-auto with a concern), present the retro handoff with explicit next
   actions (`run retro now` or `defer`). Deferral is always honored regardless
   of mode.

The primary retro trigger point is completion in `agent-coding`, when the spec
state and learnings are freshest. Retro is also where the PR URL is written
to `meta.yaml.completion.pull_requests` via `capture-pr.{sh,ps1}`, sourcing
the URL from session context when auto-chained or from
`gh pr list --head <branch> --state all --json url --limit 1` when run
standalone. If retro is explicitly deferred, resume later with `spec-retro`
in single-spec mode for that completed spec.

### Recording learnings

Learnings capture knowledge that transcends the specific code change. Add them
to `meta.yaml` under `learnings:` with these fields:

- `type` — small category field. Start with these common types:
  `pattern_discovered`, `pattern_missing`, `constraint_found`,
  `assumption_invalidated`, `assumption_confirmed`, `decision_made`,
  `tooling_created`, `scope_deviation`
- `summary` — one-line description
- `context` — why this matters, how it was discovered
- `tags` — freeform tags for discoverability; use them alongside `type`, not
  instead of it
- `date` — when it was captured

For full type definitions and extension guidance, see spec-format.md.

## Advisory spec dependencies

`depends_on` and `blocked_by` are optional `meta.yaml` fields for sequencing
related specs. They inform tooling and handoffs, but they do not change the
lifecycle status model or create hard transition gates by themselves.

- `depends_on: ["SPEC-030"]` is lightweight sequencing. When `agent-coding`
  picks up a spec, it warns if any listed upstream spec is not yet `done`.
- `blocked_by` is stronger advisory metadata. Each entry must include `spec`
  and `until_status`.
- `blocked_by.until_status: ready` is satisfied by upstream statuses `ready`,
  `in_progress`, `blocked`, or `done`.
- `blocked_by.until_status: done` is satisfied only by upstream status `done`.
- Missing or cancelled upstream specs still produce warnings because the
  dependency is not satisfied.
- `blocked` remains reserved for real execution-time blockers discovered while
  working, not planned ordering between otherwise valid specs.
- In batch creation, `create-spec` may scaffold multiple draft specs and
  express ordering with `depends_on`; research and `ready` promotion still
  happen one spec at a time.

## Parallel work

When multiple specs are in flight, their blast radius classification (recorded
in `meta.yaml` under `coordination.blast_radius`) guides sequencing:

- **`structural`** specs create or modify shared infrastructure. Merge these
  before starting parallel work on specs that depend on the same foundation.
- **`isolated`** specs are self-contained. Safe to work on in parallel.
- **`mixed`** specs contain both structural and isolated elements. Split the
  structural piece into its own spec when possible, so it can be merged first.

**Structural-first sequencing:** in a team working multiple specs, execute and
merge `structural` specs before branching into parallel `isolated` work. This
prevents merge conflicts and avoids the stacked-branch problem where parallel
work builds on divergent foundations.

**Greenfield repos** should establish shared patterns (schema, app shell, auth,
routing) before parallelizing. In near-empty repos, most early specs will be
`structural`. The transition from "everything is foundational" to "patterns are
established" is the point where parallel work becomes safe.

The classification is advisory — it informs sequencing decisions but does not
create lifecycle gates. `agent-coding` does not block based on blast radius.

## Spec numbering

Spec numbers are allocated sequentially but may not be contiguous. Gaps arise
when a claimed number is never used (abandoned draft, cancelled spec) or when
offline allocation produces a collision that is resolved by renumbering — see
`.cursor/skills/create-spec/references/renumbering.md` for the procedure and
manual follow-up checklist. Gaps are expected and do not indicate missing
work.

## Spec files and branches

Spec files may be committed by `create-spec` on a `planning-*` or `SPEC-*`
branch, or by `agent-coding` on a `SPEC-*` branch. They land on the default
branch when their PR merges. This means:

- A `draft` or `research` spec may exist only on a planning or feature branch
- A `done` spec lands on the default branch with its implementing code
- `meta.yaml` evolves through the lifecycle on the branch and merges with the
  final state

### Branch strategy

Every change goes through a branch and a PR. The branch type depends on the
workflow:

| Branch pattern | Created by | Purpose |
|----------------|------------|---------|
| `SPEC-{n}-{slug}` | `create-spec` (build-now) or `agent-coding` | Implementation work for a single spec |
| `planning-{slug}` | `create-spec` (batch/planning) | Batch spec creation — multiple specs land on one branch, one PR |
| `retro-{slug}` | `spec-retro` (multi-spec sweep) | Ledger, rules, and docs promotions from a sweep retro |
| `retro-SPEC-{n}` | `spec-retro` (deferred single-spec) | Promotion commits when the implementation branch no longer exists |

The optional `branching` block in `meta.yaml` overrides the default base/target
for `SPEC-*` branches:

**Default (no `branching` block):** Branch from the default branch, PR to the
default branch. All existing specs use this path; behavior is unchanged.

**Stacked specs (`base_branch`):** When a spec depends on unmerged work from
another spec, set `branching.base_branch` to the prerequisite's branch name.
`agent-coding` forks from that branch instead of the default branch. The PR
still targets the default branch unless `target_branch` is also set.

**Integration branch (`target_branch`):** When multiple specs feed a single
feature, set `branching.target_branch` to a short-lived integration branch.
Each spec PR merges there; one final PR merges the integration branch to the
default branch.

### Trunk-based guardrails

The trunk-based branching mandate remains: all code flows to one default branch
via short-lived branches. The branching fields do not weaken this — they
configure the topology of short-lived branches, not create permanent
non-trunk branches.

- **Stacked branches** resolve to trunk when the base spec's PR merges. If the
  base PR is squash-merged, commit hashes change and dependent branches lose
  their common ancestor — this produces conflicts on rebase. Document this as a
  known interaction when using stacked specs with squash-merge repos.
- **Integration branches** must be short-lived (days, not weeks), regularly
  synced with trunk, and deleted after all constituent specs complete and the
  final PR merges. They are not permanent feature branches.
- **GitHub auto-retarget:** when a PR's base branch merges and is deleted,
  GitHub retargets dependent PRs to the merged branch's base (typically the
  default branch). This requires the "delete branch after merge" repo setting
  and is the expected safety net for stacked spec workflows.
- No permanent non-trunk branches are permitted under the Creator process.

## Git operations

Shared conventions for commit and push behavior. All skills reference this
section rather than defining their own.

### Commit message format

For Creator-managed work tied to an active or source spec, use:

    <type>(SPEC-<n>): <short summary>

Use the current spec ID as the scope. In `spec-retro`, use the completed
source spec ID for promotion commits tied to that spec.

For Creator-managed workflows with no active or source spec, use:

    <type>: <short summary>

Do not invent placeholder or fake `SPEC-*` scopes for non-spec work such as
`repo-setup` scaffolding.

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

These six types are a **closed set** for this project. The Conventional Commits
spec only mandates `feat` and `fix`; all other types are optional and
project-defined. A small, purpose-driven list reduces classification ambiguity
and keeps type-based filtering useful.

#### Excluded Conventional Commit types

| Standard CC type | Mapping | Rationale |
|------------------|---------|-----------|
| `perf` | `refactor` (or `fix` if correcting a perf bug) | Performance improvement without behavior change is a refactor |
| `build` | `chore` | Build system and dependency changes are maintenance |
| `ci` | `chore` | CI pipeline changes are maintenance |
| `style` | `chore` | Formatting-only changes are maintenance |
| `revert` | Use the type of the original commit being undone (fallback: `chore`) | Reverts undo a prior change; classify by the original purpose |

#### Lifecycle artifact commits

Commits that touch spec metadata, ledger entries, or similar lifecycle artifacts
use existing types — classify by purpose, not by file:

| Artifact | Example commit | Type rationale |
|----------|----------------|----------------|
| Spec status transition | `docs(SPEC-042): transition to done` | Documenting lifecycle state |
| Ledger promotion | `docs(SPEC-042): promote scoped commit guidance` | Reference content promotion |
| Retro curation | `docs(SPEC-042): curate learnings` | Reference content update |
| Spec creation (batch) | `docs: scaffold SPEC-050 through SPEC-055` | Explanatory scaffolding |
| Rule or skill behavior change | `refactor(SPEC-038): extract mode references` | Alters agent behavior |

Do not invent ad-hoc types like `spec:`, `ledger:`, or `retro:`.

#### Squash-merge commits

When a PR is squash-merged, the resulting commit on the default branch follows
the **PR title format** (`SPEC-<n>: <short title>`), not the per-commit format.
This is by design — squash-merge commits represent the merged unit of work, and
GitHub derives their message from the PR title. Individual commit messages from
the feature branch are preserved in the squash commit body.

Choose the type from the primary effect of the change, not from the file
extension:

- Use `feat`, `fix`, `refactor`, or `chore` for markdown-based skills, rules,
  prompts, or specs when the change alters agent behavior, workflow defaults,
  repo operations, or other expected outcomes.
- Use `docs` only when the change is primarily explanatory or reference content
  and does not change expected behavior or workflow outcomes.
- Use `test` when the primary purpose is adding or adjusting verification.
- If a change both updates behavior and explains it, prefer the
  behavior-driving type.

Examples:
- `feat(SPEC-022): scope spec-driven commit defaults`
- `fix(SPEC-035): correct skill change-type selection guidance`
- `docs(SPEC-022): link SPEC-022 PR`
- `docs(SPEC-022): promote scoped commit guidance`
- `chore: scaffold Creator process files`

Add a body after a blank line to explain *why*, not *what*. These defaults
match the commit section in `cursor-rules-baseline.md`.

### Command patterns

    git add <specific files>
    git commit -m "<type>(SPEC-<n>): <short summary>"
    git commit -m "<type>: <short summary>"
    git push -u origin HEAD

Use the scoped form when work is tied to a spec; use the unscoped form only
when no active or source spec exists. Stage specific files — avoid `git add .`.
Prefer small, focused commits.

### Resolving the default branch

Never hard-code `main` or `master` as the default branch — the actual name
varies by repo. When a skill requires "the repo's default branch", resolve it
at runtime:

    git symbolic-ref --short refs/remotes/origin/HEAD

This returns the remote-prefixed name (e.g. `origin/main`). Use it
directly as a start-point for branching, or strip the prefix for local checkout:

    # Branch from the default branch without hard-coding its name
    git checkout -b <branch-name> origin/HEAD

    # Switch to the default branch for direct commits (e.g. repo-setup scaffolding)
    git checkout $(git symbolic-ref --short refs/remotes/origin/HEAD | sed 's|^origin/||')

### PR title format

For Creator-managed PRs tied to a single active or source spec, use:

    SPEC-<n>: <short title>

Derive the title from the spec's `title` field in `meta.yaml` or `spec.md`
frontmatter. Do not invent new wording — the spec identity is the title.

For Creator-managed PRs with no single spec (multi-spec, non-spec scaffolding):

    <descriptive title without a SPEC-* prefix>

Do not invent placeholder or fake `SPEC-*` prefixes for PRs that are not
single-spec work.

Examples:
- `SPEC-035: Spec-scoped PR title defaults`
- `SPEC-022: Spec-scoped conventional commit defaults`
- `Scaffold Creator process files` (non-spec)
- `Clarify Creator profile behavior across specs 023 and 024` (multi-spec)

### When to push

- **Feature branches** (`SPEC-*`, `planning-*`, `retro-*`): commit after each
  working state; push once before opening the PR. On a `SPEC-*` branch the
  `spec-retro` auto-chain lands its own commits (including the PR URL write
  into `meta.yaml.completion.pull_requests`) and pushes them after curation
- **Default branch** (repo-setup scaffolding only): push immediately after
  committing
- **Status transitions** (`blocked`, `cancelled`): commit and push immediately
  to persist state across sessions

### Automatic rebase before push

During the `agent-coding` completion workflow, the agent fetches the target
branch and rebases the feature branch before pushing. This keeps the branch
current when parallel specs have landed since the branch was created.

**Sequence:** fetch → check divergence → dry-run conflict detection → backup →
rebase → verify → push with `--force-with-lease` (or abort and restore on
failure).

**Target branch resolution:** read `branching.target_branch` from `meta.yaml`;
if absent, use the repo's default branch.

**When users provide input:**

| Situation | Tag | User sees |
|-----------|-----|-----------|
| Branch is up to date | *(none)* | Nothing — rebase is skipped |
| Rebase succeeds, no conflicts | `[NOTE]` | Guided: informed. Others: silent. |
| Simple conflicts resolved | `[CHECK]` | Guided/safe-auto: asked to confirm. Expert/streamlined: informed. |
| Non-trivial conflicts | `[STOP]` | All modes: agent stops, branch restored, options presented. |

**Safety constraints:**

- Auto-rebase only on `SPEC-*` branches; never on `main` / default branch
- Always create a backup branch before rebasing
- Push with `--force-with-lease` after rebase (never `--force`)
- If rebase fails and cannot be resolved, abort and restore from backup

Command patterns for rebase operations:

    git fetch origin <target_branch>
    git merge-tree --write-tree HEAD origin/<target_branch>
    git branch SPEC-<n>-backup
    git rebase origin/<target_branch>
    git rebase --abort
    git push --force-with-lease -u origin HEAD

## What v0 does NOT cover

These lifecycle features are deferred to post-boot-camp:

- **`superseded` status** — replaced by a newer spec (`superseded_by` field). Use `cancelled` for now.
- **Merge- or default-branch-triggered retro automation** — v1 uses the
  completion-triggered handoff from existing spec artifacts. Webhooks, CI jobs,
  and other external automation are future enhancements.
