# Co-coding Mode (Steps 5b–7b)

Human-driven execution path for agent-coding. The human drives the session
with small, focused increments and evaluates each result before continuing.

## Step 5b: Work in small increments

The human drives the session. For each prompt:

1. Make one small, focused change
2. Explain what you changed and why
3. Wait for the user's reaction before continuing

Do NOT batch multiple ACs into a single change. Let the user evaluate each
result before moving on.

Small within-scope clarification and polish are fine. Meaningfully new asks
must go through Step 6b before you keep iterating.

## Step 6b: Capture discovered intent

New requirements often emerge during co-coding. Before you add anything not
already covered by the spec's ACs, re-anchor the conversation:

1. Summarize the current spec goal, the AC in flight, and what is still open.
2. Classify the new ask:
   - If it is a within-scope clarification, polish pass, or small follow-up fix
     needed to satisfy the current AC, keep iterating normally.
   - If it is intentional new work that still fits this spec, confirm the user
     wants it in this spec, then add or update the AC in `spec.md` and record a
     `scope_deviation` learning in `meta.yaml`.
   - If it implies a new phase, a separate spec, or another conversational
     pivot before closure, stop iterating, use the same `continue` /
     `re-scope` / `split` / `pause` vocabulary to choose what happens next, and
     recommend `split` or a fresh session when the ask is clearly separate.
3. Do NOT silently absorb meaningfully new work as another AC.

## Step 7b: Verify ACs with the user

Walk through each AC (including any added during the session) and ask the user
to confirm it's met. The user's judgment is authoritative in co-coding mode.

`[GATE]` — acceptance-criteria closure is never skipped.

If the user says an AC is not met, iterate on it (return to Step 5b for that
AC) until the user confirms. Do not proceed to Step 8 with unmet ACs.

If the user keeps pivoting instead of confirming closure, return to Step 6b and
re-anchor the spec rather than continuing indefinitely.
