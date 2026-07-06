<!-- Shared reference: canonical source is `.cursor/skills/_shared/spec-format.md`. Edit there, then run `./sync.sh`; do not hand-edit copied `references/` files. -->

# Spec Format Reference

Complete field definitions for the two-file spec format. For the core workflow, see the parent SKILL.md.

## Directory convention

Every spec is a directory under `.spec/` containing two files:

```
.spec/
  SPEC-042-add-batch-payment/
    spec.md          # Intent (narrative)
    meta.yaml        # Lifecycle + learnings (structured)
    resources/       # Optional supporting files
```

- Directory name: `SPEC-{n}-{slug}/` where `{n}` is repo-scoped sequential and `{slug}` is a lowercase hyphenated description.
- Always a directory, never a single file — uniform convention eliminates tooling conditionals.
- `.spec/` is a hidden directory (signals "tooling surface," keeps repo root clean alongside `.git/`, `.cursor/`).
- Optional `resources/` subdirectory for supporting files (API contracts, design docs, research notes). Capture enough context inline in `spec.md` that missing resources don't block execution.

## spec.md fields

### Frontmatter

| Field | Required | Values | Purpose |
|-------|----------|--------|---------|
| `id` | Yes | `SPEC-{n}` | Repo-scoped sequential identifier |
| `title` | Yes | Free text | Human-readable title |
| `category` | Yes | `feature` \| `bug` \| `refactoring` \| `testing` | Drives template selection, metrics, and filtering |
| `owner` | Yes | `git config user.name` | Currently accountable person; set at creation, updated at implementation when the implementer differs |
| `authored_by` | Yes | `augmented` \| `automated` | Who drives: `augmented` = human with AI assistance, `automated` = agent generates, human reviews |

Frontmatter is deliberately minimal. Mutable state lives in `meta.yaml`.

### Universal body sections (all categories)

| Section | Required | Purpose |
|---------|----------|---------|
| **Problem statement** | Yes | What problem, who is affected, why it matters |
| **Acceptance criteria** | Yes | Numbered, testable criteria describing observable outcomes (not implementation steps) |
| **Research** | Before `ready` | Synthesized findings with concise provenance — conclusions, constraints, risks, and open questions that shape the rest of the spec |
| **Scope boundaries** | Yes | What is explicitly out of scope |
| **Implementation guidance** | Recommended | Repo-root-relative file paths for working-repo files, patterns, test expectations — highest-impact input for agent quality |

### Path portability

- For files inside the working repo, use repo-root-relative paths such as
  `README.md`, `src/routes/payments.ts`, or
  `.cursor/skills/create-spec/SKILL.md`.
- Do not commit local absolute filesystem paths such as `/home/...` or
  `/Users/...` in `spec.md` or `meta.yaml`.
- If you need to mention a local-only artifact outside the repo, describe it
  generically or anonymized instead of pasting a machine-specific path. For
  `meta.yaml` origin fields, prefer a shareable URL, tracking ID, or generic
  breadcrumb.

### Category-specific sections

These are recommended, not enforced by the format. The skill suggests them based on category.

**Feature** — User scenarios, Non-functional requirements

**Bug** — Reproduction (required: exact inputs, wrong output, expected output), Error evidence, Root cause analysis, Blast radius

**Refactoring** — Current state (required), Target state (required), Behavioral equivalence (required), Migration strategy

**Testing** — Coverage targets (required), Test infrastructure, Priority

## meta.yaml fields

### Core fields

| Field | Required | Type | Purpose |
|-------|----------|------|---------|
| `schema_version` | Yes | String | Format version (`"2026.04"`) |
| `status` | Yes | Enum | Current lifecycle state (see lifecycle.md) |
| `created` | Yes | Date | When the spec was created |
| `updated` | Yes | Date | Last modification date |

### Origin fields (optional)

| Field | Type | Purpose |
|-------|------|---------|
| `source` | URL/String | Where the spec originated (shareable breadcrumb, not a dependency; never a local filesystem path) |
| `tracking_id` | String | External reference (Notion task, Jira ticket) |

### Dependency fields (optional, advisory)

| Field | Type | Purpose |
|-------|------|---------|
| `depends_on` | List of `SPEC-*` IDs | Lightweight sequencing; downstream work should usually wait for each listed spec to reach `done` |
| `blocked_by` | List of objects | Stronger advisory blockers; each entry records an upstream spec ID plus the threshold that clears the warning |

Use these machine-readable shapes in `meta.yaml`:

```yaml
depends_on:
  - "SPEC-030"

blocked_by:
  - spec: "SPEC-030"
    until_status: "ready"  # ready | done
```

`depends_on` is shorthand for "usually do this after the upstream spec is done."
`blocked_by` is still advisory, not a hard lifecycle gate, but it carries an
explicit threshold so tooling can warn precisely. `blocked_by.until_status` is
required for every entry and limited to `ready` or `done`.

### Coordination fields (optional)

| Field | Type | Purpose |
|-------|------|---------|
| `coordination.blast_radius` | Enum: `structural` \| `isolated` \| `mixed` | Agent-assessed impact classification for parallel-work coordination |
| `coordination.parallel_safe` | Boolean | Derived from `blast_radius`: `true` when `isolated`, `false` otherwise |

```yaml
coordination:
  blast_radius: structural   # structural | isolated | mixed
  parallel_safe: false        # true only when blast_radius is isolated
```

The `create-spec` skill populates this block during the blast radius assessment
step. The agent — not the user — classifies the spec based on heuristic
evaluation of the spec's scope against the repo's current structure.

- **`structural`** — creates or modifies shared infrastructure that other
  features depend on. Team should merge before starting parallel work.
- **`isolated`** — self-contained change within an established boundary. Safe
  for parallel work.
- **`mixed`** — contains both structural and isolated elements. Consider
  splitting the structural piece into its own spec.

`parallel_safe` is derived and should not be set independently. It exists for
machine readability so tooling can filter specs without parsing the enum.

### Branching fields (optional)

| Field | Type | Purpose |
|-------|------|---------|
| `branching.base_branch` | String (branch name) | Branch to fork from when creating the spec's working branch; defaults to the repo's default branch when absent |
| `branching.target_branch` | String (branch name) | PR base branch; defaults to the repo's default branch when absent |

```yaml
branching:
  base_branch: "SPEC-033-staleness-aware-re-research"
  target_branch: "feature/batch-payments"
```

Three use cases:

- **Default (no block):** Agent branches from the default branch and PRs back
  to it. Zero behavior change for existing specs.
- **Stacked specs:** Set `base_branch` to the prerequisite spec's branch (e.g.
  `SPEC-033-staleness-aware-re-research`). The agent forks from that branch.
  `target_branch` is typically omitted (PR targets the default branch).
- **Integration branch:** Set `target_branch` to a short-lived integration
  branch (e.g. `feature/batch-payments`). Multiple spec PRs merge there; one
  final PR merges the integration branch to the default branch.

Both fields are advisory metadata that `agent-coding` reads at execution time.
They do not create lifecycle gates. When `target_branch` differs from the
default branch, `agent-coding` emits a visible note that the spec's work is not
on trunk until the target branch itself merges. See lifecycle.md for branch
strategy constraints and guardrails.

### Freshness fields (optional, advisory)

| Field | Type | Purpose |
|-------|------|---------|
| `ready_sha` | String (full commit SHA) | Git `HEAD` snapshot recorded when the spec most recently reached `ready`; `agent-coding` may compare watched `Files likely affected` paths against the current `HEAD` before moving to `in_progress` |

Populate `ready_sha` only at the approved `research` -> `ready` transition.
This is advisory execution metadata, not a lifecycle gate:

- If `ready_sha` is absent (older specs, manual specs), execution skips the
  freshness comparison silently.
- If `ready_sha` is invalid or cannot be compared cleanly in the current repo
  state, execution still proceeds; tooling may emit a brief note but must not
  fail the transition.
- The comparison is path-limited: diff `ready_sha` against the current `HEAD`
  only for repo files listed in **Implementation guidance** -> **Files likely
  affected**.
- `updated` may still be used as a coarse age heuristic for how long a spec has
  sat in `ready`, but `ready_sha` is the authoritative code snapshot for
  watched-file drift warnings.

### Completion fields (populated when status reaches `done`)

| Field | Type | Purpose |
|-------|------|---------|
| `completion.date` | Date | When work was completed |
| `completion.acceptance_criteria_waived` | List | ACs not met, each with `acceptance_criteria` (description) and `rationale` |
| `completion.self_review_waived` | List | `pr-review` blocking findings the user accepted to proceed with, each with `finding` (description) and `rationale` |
| `completion.pull_requests` | List of URLs | Implementing PR(s) |

Status `done` means all acceptance criteria met unless listed in `acceptance_criteria_waived`. No redundant "met" list — the waived list captures exceptions. Reference ACs by description (not positional number) for stability as specs evolve.

`self_review_waived` is distinct from `acceptance_criteria_waived`: an AC waiver means "AC not met, with rationale", while a self-review waiver means "AC met, but `pr-review` returned `request changes` or `reject` and the user explicitly accepted the flagged concern to proceed". The two concerns are semantically distinct and live in separate machine-readable fields; do not conflate them. See `agent-coding`'s completion workflow sub-step 5 for when the field is populated.

### Learnings (typed, machine-readable)

Each learning has both a typed category and freeform tags:

| Field | Required | Purpose |
|-------|----------|---------|
| `type` | Yes | Low-cardinality category for filtering (see starter types below) |
| `summary` | Yes | One-line description |
| `context` | Yes | Why this matters, how it was discovered |
| `tags` | Yes | Freeform tags for machine discoverability; not a replacement for `type` |
| `date` | Yes | When the learning was captured |

### Learning types

| Type | When to use |
|------|-------------|
| `pattern_discovered` | Found an existing codebase pattern that wasn't documented |
| `pattern_missing` | Expected a pattern to exist but it didn't — had to create one |
| `constraint_found` | Discovered a technical, performance, or business constraint |
| `assumption_invalidated` | A premise in the original spec turned out to be wrong |
| `assumption_confirmed` | A premise was verified and is worth recording |
| `decision_made` | A design or implementation choice made during execution that wasn't specified upfront |
| `tooling_created` | Created reusable test infrastructure, utilities, or helpers |
| `scope_deviation` | Work deviated from the original spec scope — captures why and what changed |

These eight values are the starter/common set. Teams can add types as patterns
emerge. Keep `type` low-cardinality so it remains useful for categorization;
use `tags` for more specific freeform discoverability.

### How learnings differ from git history

Git captures what changed in the code. Learnings capture what was discovered about the problem domain, the codebase, or the process — knowledge that transcends the specific code change. A git diff shows "added duplicate detection logic." A learning says "batch endpoints in this codebase need intra-payload duplicate detection because the DB-level uniqueness check doesn't cover within-request duplicates."

Learnings are forward-looking: they exist to help the next person (or agent) working in this area.
