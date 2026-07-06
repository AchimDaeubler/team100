---
name: user-setup
description: >
  Create or update the local per-user Creator profile. Guides the user through a
  short recommendation-first setup flow, repairs invalid profiles, and writes
  `.spec/user-config.yaml` safely. Use when the user says "run user-setup",
  "set up my Creator profile", "configure my user profile", or "personalize
  Creator for me".
---

# User Setup

Configures the optional local Creator profile for the current user in this
repo. It is per-user, not repo-wide, and does not depend on `repo-setup`.

## Workflow

Follow these steps in order. Keep the interaction brief and
recommendation-first.

### Step 1: Prepare the target path

1. Use `.spec/user-config.yaml` as the canonical output path.
2. If `.spec/` is missing, create it so the canonical path exists. This is not
   full repo setup.
3. If `.spec/.gitignore` exists, preserve it. If it does not clearly ignore
   `user-config.yaml`, continue anyway and remind the user the file should stay
   uncommitted. `repo-setup` can add the ignore rule later, but it is not a
   prerequisite here.

### Step 2: Inspect the current profile

1. Check whether `.spec/user-config.yaml` already exists.
2. Validate it against [references/user-profile.md](references/user-profile.md):
   `schema_version` and `mode` with one of the four allowed values.
3. Classify the current state:
   - **Missing:** say conservative defaults (`mode: safe-auto`) remain safe and
     this flow is the recommended way to personalize them.
   - **Valid:** summarize the current mode in plain language and ask whether to
     keep it, adjust it, or regenerate the file.
   - **Invalid or incomplete:** say the file cannot be fully honored, summarize
     what is wrong if that is easy to explain, and offer to repair or
     regenerate it through the guided flow.
   - **Legacy schema (has `behavior:` block):** the file works but carries
     outdated knobs. Offer to clean it up — keep the mode, drop the `behavior:`
     block. If the user declines, proceed with the existing mode and ignore the
     `behavior:` block.
   - **Legacy mode (`leader`):** the file uses a renamed mode value. Offer to
     update `leader` to `streamlined` — same behavior, updated name. If the
     user declines, treat `leader` as `streamlined` and proceed.
4. Treat the distinction between missing, invalid, and legacy as user-visible.
   Do not collapse them into one generic message.

### Step 3: Recommend a starting mode

1. Ask one high-level plain-language question about how hands-on versus
   autonomous the user wants Creator to be.
2. Map that answer to a recommended mode:
   - `guided`: more coaching, more confirmation, detailed explanations, and
     explicit approval before routine git operations
   - `safe-auto`: balanced default with clear checkpoints; signal-gated
     checkpoints auto-proceed when signals are clean
   - `expert`: minimal coaching, terse explanations, and auto-proceed at
     routine milestones
   - `streamlined`: outcome-focused, no git terminology, minimal interaction
     friction; only gates and mandatory stops pause
3. Default recommendation if the signal is ambiguous: `safe-auto`.
4. Use plain-language descriptions:
   - guided: "I'll walk you through every decision and explain concepts along
     the way"
   - safe-auto: "I'll handle routine steps automatically and pause at key
     decision points"
   - expert: "I'll be brief and autonomous — you'll see summaries, not
     step-by-step confirmation"
   - streamlined: "I'll focus on outcomes using plain language — technical
     details stay behind the scenes"
5. After the mode recommendation, surface the two subagent toggles with
   `true` as the recommended default for both:
   - `research_subagents` (default `true`): "Research runs as a team of
     parallel investigators — faster wall-clock time for the checkpoint, but
     there's a brief pause while background agents spin up. Flip to `false`
     to watch each research step happen inline."
   - `review_subagents` (default `true`): "PR reviews run as a team of
     parallel reviewers — each dimension checked independently, but there's
     a brief pause while background agents spin up. Flip to `false` to watch
     each review dimension happen inline."
6. Offer two paths:
   - **Fast path:** accept the recommended mode **and** both subagent
     toggles (`true`, `true`) in one confirmation.
   - **Adjust path:** hear more about each mode or flip either toggle
     before choosing.
7. If the user wants more explanation before choosing, explain the trade-offs
   in plain language rather than quoting schema names alone. Treat the two
   toggles as independent — flipping one does not imply the other.

When a pause is required regardless of mode, Creator labels it with one of five
tags from [references/agent-tags.md](references/agent-tags.md): `[STOP]`,
`[GATE]`, `[CHECK]`, `[SIGNAL]`, or `[NOTE]`. `[STOP]` and `[GATE]` always
block. The others vary by mode per the behavior grid in `agent-tags.md`.

### Step 4: Confirm before writing

1. Summarize the proposed mode in plain language and show the YAML that would
   be written.
2. Remind the user:
   - the file path is `.spec/user-config.yaml`
   - the file is local-only and should remain uncommitted
   - each collaborator can run `user-setup` independently
3. If there is already a valid profile and the proposal is unchanged, ask
   whether to leave it as-is instead of rewriting it.
   `[GATE]` — explicit approval required before changing local profile state.
4. Only write or rewrite the file after explicit user confirmation.

### Step 5: Write the profile

Write a small human-readable YAML file in this shape:

```yaml
schema_version: "2026.04"
mode: safe-auto
research_subagents: true
review_subagents: true
```

Rules:

- Ensure `.spec/` exists before writing.
- Write `.spec/user-config.yaml` directly from the guided answers; do not
  require manual YAML editing.
- Always write both subagent toggles explicitly, even when set to the
  recommended `true` default — the file is easier to edit later when the
  fields are already present.
- Do not commit the file.
- Do not create `.spec/user-config.example.yaml` just to make the flow work.
- If repairing an invalid file, prefer rewriting the full file cleanly over
  partially patching broken YAML.
- If cleaning up a legacy file, drop the `behavior:` block entirely. The mode
  alone governs all behavior.

### Step 6: Close cleanly

1. Re-state the final mode in plain language using the descriptions from Step 3.
2. Re-state whether the file appears protected by `.spec/.gitignore` or whether
   the user should double-check that it remains uncommitted.
3. Mention that the flow is safe to re-run whenever the user wants a different
   mode.

## Gotchas

- NEVER conflate with team settings — this configures one user's local profile for this repo.
- ALWAYS lead with a recommended mode — let the user adjust only what matters instead of a long survey.
- IF the profile is invalid or partial, THEN offer repair or regenerate — NEVER request manual YAML debugging.
- IF the profile has a legacy `behavior:` block, THEN offer to clean it up by dropping the block and keeping the mode.
- NEVER depend on `.spec/user-config.example.yaml` — the guided flow must work without it.
- NEVER overwrite a valid profile silently — summarize existing settings and confirm before rewriting.

## When NOT to use this skill

- Creating or researching a spec → `create-spec`
- Executing a ready spec → `agent-coding`
- Setting up repo scaffolding or `.cursor/rules/` → `repo-setup`
- Reviewing an agent-authored PR → `pr-review`
- Curating learnings from completed specs → `spec-retro`

## Reference

- [references/user-profile.md](references/user-profile.md) — Canonical schema,
  mode definitions, and setup guidance
