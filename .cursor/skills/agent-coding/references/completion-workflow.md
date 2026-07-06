# Completion Workflow (Step 8)

Post-verification workflow for agent-coding. Run when all acceptance criteria
are verified in either unsupervised or co-coding mode.

**Preflight:** Before starting the completion steps below, verify that `gh`
(GitHub CLI) is available (`Get-Command gh` / `command -v gh`). The workflow
requires `gh` at sub-step 7 for `gh pr create`. If `gh` is missing, stop with:

> **GitHub CLI (gh)** is not installed. It is required for creating the pull
> request (completion sub-step 7). Install from https://cli.github.com/ and
> retry the completion workflow.

Do not proceed through sub-steps 1–6 only to fail at PR creation.

When all ACs are verified:

1. Run `.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> done`
   (PowerShell) or `.cursor/skills/create-spec/scripts/transition.sh
   <spec-directory> done` (bash/zsh) to set `status: done`, update the date,
   and create the `completion` block with `pull_requests: []`. If any ACs were waived, manually add
   `acceptance_criteria_waived` with rationale to `meta.yaml`.

2. Record learnings in `meta.yaml` for anything discovered during execution:
   patterns found or missing, assumptions confirmed or invalidated, constraints
   discovered, decisions made that weren't in the spec.

3. Before committing, run a quick refinement pass on changed files: make sure
   each remains scannable, remove superseded wording, duplicate wrappers,
   boilerplate, or structure added only for ceremony, then commit spec files
   (`spec.md`, `meta.yaml`) alongside code changes — follow
   [Git operations](lifecycle.md#git-operations).

4. Advisory commit-message check: verify that the most recent commit message
   matches the allowed format in
   [Commit message format](lifecycle.md#commit-message-format) — scoped
   `<type>(SPEC-<n>): <summary>` or unscoped `<type>: <summary>` with one of
   the six allowed types. If the message does not match, warn visibly but do
   not block or amend automatically.

5. `[SIGNAL]` — Self-review auto-chain. This is the primary review-coverage
   trigger point because the local diff, spec context, and fix cost are
   freshest here. Assemble the review context (current spec identity, spec
   path, target branch resolved from `branching.target_branch` in `meta.yaml`
   when set, else the repo default branch) and then fork by mode:

   **Clean-signal criteria:** all ACs verified and met, working tree has the
   spec and code changes committed or staged, on a `SPEC-*` branch matching
   this spec, and the user has not requested deferral.

   **Escalation triggers:** ACs waived without rationale, AC verification
   surfaced unresolved failures, or explicit deferral request. Degrade one
   tier (inform → prompt → block) per the `[SIGNAL]` grid in
   `references/user-profile.md`.

   - **guided:** Block with a prompted handoff. Present the review context and
     ask the user whether to run self-review now or defer.
   - **safe-auto (clean signal):** Inform that self-review is starting, then
     invoke the `pr-review` skill in self-review mode using the assembled
     context.
   - **safe-auto (concern flagged):** Escalate to a blocking prompt — present
     the concern and ask whether to run self-review now or defer.
   - **expert / streamlined:** Invoke the `pr-review` skill in self-review mode
     using the assembled context. No prompt, no pause.

   When auto-proceeding (safe-auto clean, expert, streamlined), the invocation
   is imperative: read and follow the `pr-review` skill's SKILL.md. `pr-review`
   Step 2 detects self-review mode (no open PR yet) and generates the diff
   itself, so do not pre-compute or pass the diff.

   **Halt on non-approve verdict (all modes).** If `pr-review` returns
   `request changes` or `reject`, halt the completion workflow before sub-step
   6 (rebase) and sub-step 7 (push). Surface the verdict summary, per-dimension
   pass/flag/fail results, and any blocking findings, then yield to the user.
   This clause applies regardless of mode — including `streamlined`, where
   `[SIGNAL]` is otherwise invisible — because the halt is a hard constraint,
   not a tag-tier signal.

   **Resuming a halted sub-step 5.** Resume only when one of the following is
   true: (a) the agent has made new commits addressing the blocking findings
   and re-runs self-review to a non-blocking verdict, or (b) the user
   explicitly waives the remaining findings. Captured waivers land in
   `meta.yaml` under `completion.self_review_waived` as a list of
   `{finding, rationale}` entries — parallel in shape to
   `completion.acceptance_criteria_waived` but semantically distinct (the AC
   itself is met; the user is accepting a flagged concern). Silent bypass is
   not permitted.

   **If the invocation itself errors** (skill files missing, dispatch-path
   failure with no inline fallback available, or unrecoverable tooling errors),
   record the failure in narration, surface it at the current mode's escalation
   tier, and block sub-step 6. The workflow does not silently proceed to
   rebase/push as if self-review had passed. Recovery options: restore the
   skill and retry, resolve the tooling error and retry, or explicitly waive
   self-review (captured in `completion.self_review_waived`) and resume.

6. Fetch and rebase onto the target branch. Read
   [references/conflict-resolution.md](conflict-resolution.md) and follow the
   safe rebase sequence. Resolve the target branch from
   `branching.target_branch` in `meta.yaml`, falling back to the repo's default
   branch. After rebase, push with `--force-with-lease` (never `--force`).
   Conflict tier determines the tag:

   - **Trivial** (git auto-resolves): `[NOTE]`
   - **Simple** (agent resolves mechanically): `[CHECK]`
   - **Non-trivial** (agent cannot safely resolve): `[STOP]` — abort rebase,
     restore branch, present options

   If not on a `SPEC-*` branch, or if fetch fails, skip with a warning and
   proceed to sub-step 7.

7. `[NOTE]` — Push the branch (see [Git operations](lifecycle.md#git-operations))
   and open a PR. On a dedicated `SPEC-*` branch, `[NOTE]` governs visibility
   for push and PR creation. Default-branch, destructive, and policy contexts
   always pause.

   **PR title:** Use `--title "SPEC-<n>: <spec title>"` on `gh pr create`,
   deriving the title from the spec's `title` field. For multi-spec or non-spec
   PRs, use a descriptive title without a `SPEC-*` prefix. See
   [PR title format](lifecycle.md#pr-title-format).

   **PR base branch:** Read `branching.target_branch` from `meta.yaml`. If
   present, pass `--base <target_branch>` to `gh pr create`. If absent, omit
   `--base` (the hosting platform's default applies).

   **Trunk-distance note:** When `target_branch` is set and differs from the
   repo's default branch, include a visible `[NOTE]` in the PR description:
   "This PR targets `<target_branch>`, not the default branch. The spec's work
   will not be on trunk until `<target_branch>` itself merges to the default
   branch."

8. `[SIGNAL]` — Retro auto-chain. This is the primary retro trigger point
   because the spec state, PR context, and raw learnings are freshest here.
   Retro — not this step — records the PR URL into
   `meta.yaml.completion.pull_requests` and refreshes the spec dashboard, so
   no extra commit or push lands between `gh pr create` and the retro
   handoff. Assemble the retro context (completed spec identity, completion
   state, available PR URL from `gh pr create`, raw learnings from
   `meta.yaml`) and then fork by mode:

   **Clean-signal criteria:** spec is `done` with `completion` block populated,
   raw learnings are present in `meta.yaml`, no ACs were waived without
   rationale, and the user has not requested deferral.

   **Escalation triggers:** waived ACs without rationale, empty learnings,
   missing `completion` block, or explicit deferral request.

   - **guided:** Block with a prompted handoff. Present the retro context and
     ask the user whether to run retro now or defer.
   - **safe-auto (clean signal):** Inform that retro is starting, then invoke
     the `spec-retro` skill in single-spec mode using the assembled context.
   - **safe-auto (concern flagged):** Escalate to a blocking prompt — present
     the concern and ask whether to run retro now or defer.
   - **expert / streamlined:** Invoke the `spec-retro` skill in single-spec
     mode using the assembled context. No prompt, no pause.

   When auto-proceeding (safe-auto clean, expert, streamlined), the invocation is
   imperative: read and follow the `spec-retro` skill's SKILL.md. The skill
   will detect that it arrived from an auto-chain and optimize accordingly
   (see spec-retro Step 1 and Step 2).

9. If the auto-chained retro encounters an error, surface the issue and allow
   the user to retry or defer. The completion state (`status: done`,
   learnings) is already persisted and must not be rolled back. The retry
   path is identical to a standalone `spec-retro` invocation for that
   completed spec; retro's PR URL recovery (`gh pr list --head <branch>
   --state all`) covers the case where `gh pr create` succeeded but the
   auto-chain failed before retro wrote the URL.

10. If the user defers retro (at any mode level — deferral is always honored),
    say so explicitly and provide a restart prompt such as "Run single-spec
    retro for `<SPEC-ID>` using `.spec/<SPEC-directory>/`." Treat the learning
    loop as pending, and explicitly note that
    `meta.yaml.completion.pull_requests` remains unwritten until retro runs —
    the URL is still recoverable via `gh pr list` when retro eventually runs.

11. Treat completion as a session boundary. Apply this boundary **after retro
    completes** (when auto-chained) or **after deferral** (when retro is
    skipped). Do not emit a session-boundary message before retro runs — the
    `spec-retro` skill's own end-of-session is the authoritative boundary when
    auto-chained. If the user asks "what next?" or wants to start another spec,
    give a bounded handoff (current state, next recommended step, and restart
    prompt if relevant) and recommend a fresh session for that next unit of
    work instead of continuing indefinitely in the completed execution thread.
    The next turn applies `.cursor/rules/branch-state-reconciliation.mdc`,
    so branch context auto-reconciles — including the admin-merge case (a
    PR merged between turns triggers an automatic swap to default and pull).

**What to track:** After the PR merges, note how many lines survived review
without human modification — this is the agent-authored merge rate, the primary
quality signal for unsupervised execution.
