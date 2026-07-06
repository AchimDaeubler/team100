<!-- Shared reference: canonical source is `.cursor/skills/_shared/user-profile.md`. Edit there, then run `./sync.sh`; do not hand-edit copied `references/` files. -->

# User Profile

Creator skills may consult an optional capability-aware user profile at
`.spec/user-config.yaml` in the active working repo.

This file is:

- local to one working clone
- per-user rather than per-repo
- intended to stay uncommitted
- ideally ignored via `.spec/.gitignore` so the local-only rule stays next to
  the local-only file

Different collaborators may keep different local profiles in separate clones of
the same repo.

## Canonical schema

```yaml
schema_version: "2026.04"
mode: safe-auto          # guided | safe-auto | expert | streamlined
research_subagents: true # dispatch research lanes as subagents; false runs them inline
review_subagents: true   # dispatch review lanes as subagents; false runs them inline
```

Required fields:

- `schema_version`: must be `"2026.04"`
- `mode`: `guided` | `safe-auto` | `expert` | `streamlined`

Optional fields:

- `research_subagents`: boolean. Default `true` when absent, malformed, or set
  to an unrecognized value.
- `review_subagents`: boolean. Default `true` when absent, malformed, or set
  to an unrecognized value.

No `behavior.*` block. The mode IS the complete behavioral definition.

If `mode` is missing or has an unknown value, treat the profile as invalid and
fall back to the conservative default below. If the file contains a legacy
`behavior:` block, ignore it — the mode alone governs behavior. When
`user-setup` encounters a legacy `behavior:` block, it offers to clean it up.

If `mode: leader` is encountered, treat it as `mode: streamlined` — this is a
renamed mode, not an invalid value. When `user-setup` encounters `leader`, it
offers to update the file to `streamlined`.

Unlike `mode`, an unrecognized `research_subagents` or `review_subagents`
value does **not** invalidate the profile: it silently falls back to the
`true` default with no per-field note, and is never cited individually in
fallback messages. A profile with a valid `mode` and a malformed toggle
still behaves as a valid profile — only the toggle defaults quietly.

## Conservative default

Use this when the profile is missing, incomplete, or malformed:

```yaml
schema_version: "2026.04"
mode: safe-auto
research_subagents: true
review_subagents: true
```

When falling back, continue without blocking the workflow and emit one concise
note that matches the situation:

- Missing profile:

  > No `.spec/user-config.yaml` was found, so I'm using conservative defaults
  > (`mode: safe-auto`). For a more personalized Creator flow, run `user-setup`
  > in this repo. If that skill is unavailable in your environment, use the
  > README guidance or start from `.spec/user-config.example.yaml`.

- Invalid or incomplete profile:

  > I found `.spec/user-config.yaml`, but it is incomplete or invalid, so I
  > can't fully honor it. I'm using conservative defaults (`mode: safe-auto`)
  > instead. For a more personalized Creator flow, run `user-setup` to repair
  > it. If that skill is unavailable in your environment, repair the file
  > using the README guidance or start from `.spec/user-config.example.yaml`.

## Four modes

| Mode | Interaction style | Explanation depth | Vocabulary | Git visibility |
|------|-------------------|-------------------|------------|----------------|
| `guided` | All tags block | Detailed | Technical | Explicit per-step |
| `safe-auto` | `[CHECK]` blocks; `[SIGNAL]` auto-proceeds on clean signal; `[NOTE]` informs | Standard | Technical | Bundled with decisions |
| `expert` | Only `[GATE]` and `[STOP]` block; `[CHECK]` and `[SIGNAL]` inform; `[NOTE]` silent | Terse | Technical | Bundled with decisions |
| `streamlined` | Only `[GATE]` and `[STOP]` block; `[CHECK]` informs; `[SIGNAL]` and `[NOTE]` silent | Outcome-focused | Task-level | Invisible |

## Tag behavior by mode

See [agent-tags.md](agent-tags.md) for the five-tier behavior grid and
signal-gated escalation rules. Each tag carries its full per-mode behavior
inline — no matrix cross-reference needed.

## Vocabulary translation table (streamlined mode)

When `mode: streamlined` is active, all user-facing text follows these
translations. Agents apply these when composing messages to the user; skill
instructions themselves retain technical terms for agent comprehension.

| Technical term | Streamlined equivalent | When to use |
|----------------|------------------------|-------------|
| commit | "save progress" | inform-level git summaries |
| branch | *(never surfaced)* | — |
| pull request / PR | "submit for review" | PR creation, review references |
| merge | "publish" | post-review completion |
| push | *(never surfaced)* | — |
| checkout | *(never surfaced)* | — |
| rebase | "reconcile with recent changes" | conflict resolution; escalate to `[STOP]` if non-trivial |
| conflict | "overlapping changes" | when escalating to user |
| diff | "changes" or "what changed" | review context |
| repository / repo | "project" | general references |
| staging / staged | *(never surfaced)* | — |
| HEAD / SHA | *(never surfaced)* | — |

## Subagent toggles

`research_subagents` and `review_subagents` let each clone pick how
investigation work runs. `true` (the default) dispatches the existing
parallel subagent lanes; `false` runs the same investigations inline on
the main agent, producing the same synthesized output shape.

| Toggle | Consumers | When `true` | When `false` |
|--------|-----------|-------------|--------------|
| `research_subagents` | `create-spec` research gate, `agent-coding` freshness re-research, `brainstorming` approach viability | Dispatch parallel research lanes | Main agent investigates the same evidence inline, still synthesizes by lane attribution |
| `review_subagents` | `pr-review` Step 3 | Dispatch five parallel review lanes | Main agent walks the five-dimension signal tables inline |

The toggles are orthogonal to `mode` and to each other. Toggle lookup is
cheap: each consumer reads the boolean once per workflow invocation, not
per lane or per AC. Graceful-degradation rules still apply — a failed
subagent launch or unavailable web tool falls back to inline main-agent
coverage for that lane regardless of toggle value. The toggle is the
user's explicit preference; failure fallback is automatic and
independent.

## Behavioral equivalence

- `mode: guided` produces identical checkpoint behavior to the previous
  `mode: guided` + `behavior: { confirmations: explicit, git_autonomy: manual,
  explanation: detailed }` configuration. All five tags block in guided.
- `mode: safe-auto` produces the same or fewer pauses than the previous
  safe-auto preset. Signal-gated (†) cells replace unconditional blocks with
  context-aware behavior.
- `mode: expert` matches the previous "minimal + autonomous" behavior with
  silent auto-proceed at routine milestones.
- All modes still block on: scope expansion, new dependencies, failure/thrash
  loops, destructive git operations, shared-branch writes, policy/permission
  boundaries.

## Streamlined tag visibility

When `mode: streamlined` is active, tag visibility follows these rules instead
of the default "silent means no pause, not no trace" convention:

| Tag | Streamlined behavior |
|-----|----------------------|
| `[STOP]` | block, **labeled** — tag name shown in output |
| `[GATE]` | block, **labeled** — tag name shown in output |
| `[CHECK]` | inform, **unlabeled** — natural language only, no tag name in output |
| `[SIGNAL]` | **fully invisible** — no pause, no trace in conversation |
| `[NOTE]` | **fully invisible** — no pause, no trace in conversation |

Other modes are unaffected — they retain the existing "silent means no pause,
not no trace" convention.

## Gate content elements

When presenting any `[GATE]` interaction point, include these three ingredients
in the gate message. Scale detail to the active mode. Skills with richer
gate-specific content (e.g., `pr-review`'s dimensional verdict) naturally
exceed this minimum.

| Ingredient | What to include | guided | safe-auto | expert | streamlined |
|------------|-----------------|--------|-----------|--------|-------------|
| **What-was-done** | Completed work and key decisions | Detailed narrative with rationale | Concise summary | Terse list | What changed and why it matters |
| **Completeness signal** | Checkable facts: AC counts, criteria verified, scope coverage — never model-narrated confidence | AC-by-AC walkthrough with evidence | AC counts + brief evidence | AC counts only | Fraction complete, outcome-framed |
| **Attention flags** | Risks, deviations, partial coverage, unresolved concerns | Each item with context and recommendation | Flag with brief context | Flag only | Task-level language; omit if nothing unusual |

## Streamlined meta-reference suppression

When `mode: streamlined` is active, agents do not surface in user-facing text:

- Mode names, mode system, or profile concepts
- References to `user-setup` as a configuration option
- Tag names (except `[STOP]` and `[GATE]` labels per the visibility table above)
- Narration of execution mode selection — just proceed

## Important distinction

User profile mode is not the same thing as agent execution mode.

- `guided` user mode does not forbid `unsupervised` execution
- `expert` user mode does not imply `unsupervised` execution
- `streamlined` user mode auto-selects unsupervised when ACs are clearly
  testable, presenting the selection as informational
- execution mode still depends on the task and the user's request

## Skill-integration pattern

Each profile-aware skill keeps its "Optional user profile" section short
(under 10 lines) with:

1. A check-and-apply instruction referencing this file
2. A one-sentence scope delta (what mode-dependent decisions the skill makes)
3. The skill's tags listed by tier name (e.g., "`[CHECK]` decomposition.
   `[GATE]` ready handoff. `[SIGNAL]` prior learnings. `[NOTE]` batch
   scaffolding.")

Each skill states only its specific delta, not a restatement of the general
rules.

## Setup guidance

Preferred path when `user-setup` is available:

1. Run `user-setup` in the active working repo
2. Review the recommended mode and adjust if desired
3. Confirm writing `.spec/user-config.yaml`
4. Keep `.spec/user-config.yaml` uncommitted, preferably via `.spec/.gitignore`

Manual fallback when `user-setup` is unavailable:

1. Copy `.spec/user-config.example.yaml` to `.spec/user-config.yaml`
2. Set `mode` to `guided`, `safe-auto`, `expert`, or `streamlined`
3. Keep `.spec/user-config.yaml` uncommitted, preferably via `.spec/.gitignore`
