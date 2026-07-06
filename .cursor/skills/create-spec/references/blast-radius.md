# Blast Radius Classification

Heuristic assessment procedure for Step 6 of create-spec. The agent evaluates
the spec's scope against the repo's current structure and classifies the
expected blast radius to guide parallel-work decisions.

## Classification definitions

| Classification | Meaning | `parallel_safe` |
|----------------|---------|-----------------|
| `structural` | Creates or modifies shared infrastructure that other features will depend on. Merge before parallel work begins. | `false` |
| `isolated` | Self-contained change within an established boundary. Safe to work on in parallel. | `true` |
| `mixed` | Contains both structural and isolated elements. Consider splitting the structural piece into its own spec. | `false` |

### Greenfield signals

In near-empty repos, most early work is foundational — schema, app shell, auth,
routing. Bias toward `structural` for these. The lifecycle guidance frames
greenfield coordination as "establish shared patterns first, then parallelize."
The transition from "everything is foundational" to "patterns are established"
is the hardest moment to classify; when in doubt, prefer `structural`.

### Legacy signals

In established repos, look for widely-depended-on code: shared middleware,
database schemas, core utilities, configuration systems. Modifications to these
are `structural` even if the change itself is small. Adding a self-contained
feature that only *uses* shared code (without modifying it) is `isolated`.

## Heuristic questions

Evaluate these questions against the spec's scope and the repo's current state.
Answer yes/no for each; the pattern of answers drives the classification.

**Structural signals** (any "yes" suggests `structural`):

1. Does this create files, schemas, or patterns that other features will depend
   on or import?
2. Does this modify widely-depended-on existing code (shared middleware, core
   utilities, database schemas, authentication, routing)?
3. Does this change conventions or defaults that affect how other features are
   built (build config, linting rules, shared types, API contracts)?
4. Is this repo near-empty, and does this spec establish foundational patterns?

**Isolated signals** (all "yes" suggests `isolated`):

5. Is the change contained within a single bounded context or feature area?
6. Does it only *use* shared infrastructure without modifying it?
7. Could another developer work on a different feature simultaneously without
   risk of merge conflicts from this spec's changes?

**Classification rule:**

- If any structural signal is "yes" and all isolated signals are also "yes" →
  the spec likely touches a shared file for a self-contained reason (e.g.,
  adding an isolated feature flag to a shared config). Distinguish *semantically*
  horizontal changes (affect how other features work) from *syntactically*
  horizontal ones (touch a shared file without changing its contract). The latter
  is `isolated`.
- If structural signals dominate → `structural`
- If isolated signals dominate → `isolated`
- If both structural and isolated work are present and neither is incidental →
  `mixed`

## Recording the classification

Uncomment and populate the `coordination` block in `meta.yaml`:

```yaml
coordination:
  blast_radius: structural   # structural | isolated | mixed
  parallel_safe: false        # true only when blast_radius is isolated
```

`parallel_safe` is derived: `true` when `blast_radius` is `isolated`, `false`
otherwise. Do not set it independently.

## Mode-aware guidance

After classifying, deliver guidance using `[CHECK]`. The language varies by
user profile mode.

### structural

| Mode | Guidance |
|------|----------|
| streamlined | "This builds the project's foundation. Your team should publish this before starting individual work pieces." |
| guided, safe-auto | "This spec modifies shared infrastructure. I recommend merging this before your teammates start parallel work on specs that depend on these changes. [reason]" |
| expert | "Structural — merge before parallel work. [reason]" |

### isolated

| Mode | Guidance |
|------|----------|
| streamlined | "This is safe to work on in parallel with your teammates." |
| guided, safe-auto | "This spec is self-contained. It's safe to work on in parallel with other specs. [reason]" |
| expert | "Isolated — parallel-safe. [reason]" |

### mixed

| Mode | Guidance |
|------|----------|
| streamlined | "Parts of this overlap with your project's shared foundation. Consider splitting the foundational piece into its own work item to unblock your teammates." |
| guided, safe-auto | "This spec has both structural and isolated elements. Consider splitting the structural piece into its own spec so it can be merged first, unblocking parallel work on the isolated parts. [reason]" |
| expert | "Mixed — consider splitting structural piece. [reason]" |

In all cases, `[reason]` is a brief statement of *why* the classification was
chosen (e.g., "this modifies the database schema which other features will
depend on"). Always state reasoning, not just the label.
