# Unsupervised Mode (Steps 5a–7a)

Autonomous execution path for agent-coding. The agent works through acceptance
criteria systematically with mandatory stop points enforcing quality.

## Step 5a: Execute autonomously

Work through acceptance criteria systematically. For each AC:

1. Implement the change
2. Verify it (run tests, check behavior)
3. Commit ([Git operations](lifecycle.md#git-operations)) — this
   creates a checkpoint you can fall back to if a later AC triggers a stop point
4. Move to the next AC

**Mandatory stop points** — STOP and present options when any of these occur:

| Condition | Trigger |
|-----------|---------|
| **Test failure loop** | Same test fails after 3 fix attempts |
| **Scope expansion** | Need to modify a file under "Files NOT to modify" or add functionality outside any AC |
| **New dependency** | Implementation needs a library, service, or API not mentioned in the spec |
| **Circular progress** | You've made changes, reverted, and are about to make similar changes again |
| **Off-spec request** | The user asks for work outside the current ACs and it is more than a small clarification, polish pass, or follow-up fix needed to finish the current AC |
| **Next phase / new spec** | The user asks for a clearly separate phase, another spec, or roadmap-style follow-on while the current spec is still active |
| **Repeated conversational pivot** | The conversation changes direction again before the current AC or previous pivot is closed |

For the three conversational cases above:

- First summarize the current state: active spec, AC in flight, completed work,
  and what remains.
- Treat small within-scope clarification, polish, or follow-up fixes as normal
  execution; do not force a restart for those.
- If the new ask is clearly a new unit of work, recommend `split` or a fresh
  session rather than silently absorbing it into the current spec.

## Step 6a: Present structured options at each stop

State what triggered the stop. If the stop came from conversational drift,
summarize the current state before presenting options. Then present exactly
these four options:

`[STOP]` — the user must choose how to proceed.

1. **Continue** — you have a specific plan to resolve this (explain the plan)
2. **Re-scope** — narrow the current spec to what's working, defer the rest
3. **Split** — create a new spec for the problematic part, finish what works
4. **Pause** — transition to `blocked`, document the blocker, stop work

When the new ask is clearly a separate next unit of work, recommend `Split` and
a fresh session once the current state is summarized.

Wait for the user's choice. Do not choose for them.

## Step 7a: Verify all ACs

After implementation, walk through every acceptance criterion:

`[SIGNAL]` — acceptance-criteria closure is never skipped.

- State the AC
- Describe how it was verified (test output, observable behavior, file check)
- Mark as **met** or **unmet**

If any AC is unmet, present stop-point options (Step 6a).
