# Blocked and Cancelled Handlers (Steps 9–10)

Edge-case handlers for agent-coding when execution cannot continue or the user
abandons the spec.

## Step 9: Handle blocked (when needed)

If execution cannot continue due to an external dependency:

1. Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> blocked` (PowerShell) or `transition.sh <spec-directory> blocked` (bash/zsh) to set `status` and `updated` in `meta.yaml`, then apply the `spec-dashboard` skill to refresh the spec dashboard. Manually add a learning of type `constraint_found` documenting the blocker.

2. Commit and push the status change — follow
   [Git operations](lifecycle.md#git-operations).

3. Tell the user what is blocked and what needs resolution.

4. When the blocker is resolved, transition back to `in_progress` and resume
   from where you stopped.

5. If the user pivots to different work or asks "what next?" while this spec is
   blocked, summarize the blocker and current state, then recommend a fresh
   session for that separate unit of work instead of continuing in the blocked
   execution thread.

## Step 10: Handle cancelled (when needed)

If the user decides to abandon the spec during execution:

1. Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> cancelled` (PowerShell) or `transition.sh <spec-directory> cancelled` (bash/zsh) to set `status` and `updated` in `meta.yaml`, then apply the `spec-dashboard` skill to refresh the spec dashboard. Optionally add a learning capturing why the work was abandoned.

2. Commit and push the status change — follow
   [Git operations](lifecycle.md#git-operations).

3. Do not delete the branch — it preserves context if the work is revisited.

4. If the user asks "what next?" after cancellation, summarize why the spec
   stopped and recommend a fresh session for any different unit of work.
