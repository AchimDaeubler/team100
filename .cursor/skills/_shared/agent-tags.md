<!-- Shared reference: canonical source is `.cursor/skills/_shared/agent-tags.md`. Edit there, then run `./sync.sh`; do not hand-edit copied `references/` files. -->

# Agent Tags

Inline control-flow markers for workflow pause points. Each tag carries a
fixed per-mode behavior grid — no external matrix lookup required.

## Behavior grid

| Tag | Semantic | guided | safe-auto | expert | streamlined |
|-----|----------|--------|-----------|--------|-------------|
| `[STOP]` | Mandatory halt, no recovery | block | block | block | block |
| `[GATE]` | Explicit approval required | block | block | block | block |
| `[CHECK]` | Mode-aware decision point | block | block | inform | inform |
| `[SIGNAL]` | Signal-gated auto-proceed | block | inform† | inform | silent |
| `[NOTE]` | Lightweight operational step | block | inform | silent | silent |

## Tag definitions

### `[STOP]`

Mandatory halt. Unconditional across all modes. Present structured options or
report that execution cannot proceed. No autonomous recovery.

Use for: mandatory stop-point triggers in unsupervised execution, unresolvable
blockers (missing spec, terminal state).

### `[GATE]`

Blocking approval gate. Unconditional across all modes. Require an explicit
affirmative signal ("ready", "approved", "yes") before continuing. Silence,
ambiguity, or non-affirmative responses do not satisfy the gate.

Every gate message must include three content ingredients: (1) what-was-done
summary, (2) completeness signal based on checkable facts, and (3) attention
flags for anything unusual. See the "Gate content elements" section in
[user-profile.md](user-profile.md) for mode-specific scaling. Skills with
richer gate-specific content naturally exceed this minimum.

Use for: rebuild replacements, write confirmations,
default-branch git commits (repo-setup scaffolding only), review verdicts.

### `[CHECK]`

Mode-aware decision point. Blocks in guided and safe-auto; informs in expert
and streamlined. Use when the interaction is a meaningful decision that warrants
visibility in lower-autonomy modes but can auto-proceed once the user is
experienced.

Use for: decomposition decisions, in_progress resume, retro mode selection,
skill availability unknown, docs pass.

### `[SIGNAL]`

Signal-gated auto-proceed. Blocks in guided; signal-gates in safe-auto
(inform† — auto-proceed when signal is clean, escalate when concern flagged);
informs in expert; silent in streamlined.

Use for: execution mode selection, freshness handling, AC verification
(unsupervised), prior learnings curation, ready handoff, retro curation
decisions (learning improvements, ledger curation, promotion),
post-approval follow-through, meta improvements, retro auto-chain.

### `[NOTE]`

Lightweight operational step. Blocks in guided; informs in safe-auto; silent
in expert and streamlined. Use for routine operational steps that have mode-varying
visibility but do not represent decisions.

Use for: branch creation, checkpoint commits, push + PR creation, batch
scaffolding.

## Signal-gated (†) escalation

`[SIGNAL]` cells marked † operate at their base level when automated signals
are clean, and escalate one level (silent→inform, inform→block) when a concern
is flagged. Clean-signal criteria per interaction point:

- **Prior learnings curation**: all returned learnings are relevant with no
  contradictions to other lane findings (or no notable prior learnings found)
- **Execution mode selection**: ACs are clearly testable
- **Freshness check result**: nothing stale since ready
- **Freshness proceed/targeted/full**: nothing stale since ready
- **AC verification (unsupervised)**: all ACs verified with evidence
- **Ready handoff**: research completed with no open questions, unresolved
  concerns, or notable risks worth surfacing
- **Retro curation decisions**: all recommendations are straightforward
  promotions/refinements with no contradictions, complex merges, or stale
  conflicts
- **Retro auto-chain**: spec is `done` with `completion` block populated, raw
  learnings are present in `meta.yaml`, no ACs waived without rationale, and
  user has not requested deferral

## Rules

- NEVER skip a `[STOP]` or `[GATE]` — these are unconditional across all modes.
- For `[CHECK]`, `[SIGNAL]`, and `[NOTE]`, apply the behavior grid for the
  active mode directly. No matrix cross-reference needed.
- ALWAYS wait for the user's response before continuing past a blocking tag.
- IF a `[GATE]` requires explicit approval, THEN do not infer it from silence
  or ambiguity.
- Every interaction — whether blocking, informational, or silent — produces a
  visible record in the conversation. "Silent" means "no pause," not "no trace."
- **Streamlined exception:** in `streamlined` mode, `[SIGNAL]` and `[NOTE]` are
  fully invisible (no pause *and* no trace). `[CHECK]` informs in natural
  language without showing the tag name. Only `[STOP]` and `[GATE]` show their
  tag label. See the streamlined tag visibility table in `user-profile.md`.
