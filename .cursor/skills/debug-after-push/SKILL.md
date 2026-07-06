---
name: debug-after-push
description: >
  Debug build failures, deploy failures, and runtime errors after pushing
  code. Inspects GitHub Actions via gh CLI and/or queries Datadog for
  application logs — depending on the problem. Use when the user says
  "debug build", "debug deploy", "why did my build fail", "why did my
  deploy fail", "check CI", "check logs", "check app logs", "my app is
  crashing", or reports errors after pushing.
---

# Debug After Push

| Problem | Tool |
|---------|------|
| **Build / deploy failure** | `gh` CLI → GitHub Actions logs |
| **Runtime error** (application errors, crashes, bad responses, 500s) | Datadog MCP (optional) |

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 0.
- Mode governs tag behavior and explanation depth. Does not change diagnostic logic.
- `[CHECK]` vague intent classification. `[SIGNAL]` offer to help fix. `[NOTE]` repo context gathered, Datadog unavailable.

## Prerequisites

- `gh` CLI authenticated with repo access.
- Datadog MCP — optional, only needed for runtime log checks.

## Step 0: Determine intent

`[CHECK]` — classify the user's question before doing anything else.

| Intent | Signals | Steps to run |
|--------|---------|--------------|
| **CI** | "build failed", "deploy failed", "check CI" | 1 → 2 → 4 |
| **Runtime** | "app is crashing", "500 errors", "check app logs" | 1 → 3 → 4 |
| **Vague** | "something is wrong after push", "app not working" | Ask: CI logs, runtime logs, or both? |

Only run the steps that match. If ambiguous, ask the user.

## Step 1: Gather repo context

Run `scripts/repo-context.ps1` (PowerShell) or `scripts/repo-context.sh`
(bash/zsh) to collect remote URL, current branch, HEAD SHA, service name,
and deploy branch.

Apply `.cursor/rules/branch-state-reconciliation.mdc` alongside this
context gathering — it covers the general "is the current branch the
right branch?" question (merged PR, dirty tree, ambiguous state). The
debug-specific deploy-branch comparisons in Step 2 and Step 4 below
remain intact and complement, rather than duplicate, that reconciliation.

`[NOTE]` — report the gathered context.

## Step 2: Inspect CI

### Find the relevant run

Match by **HEAD commit SHA** — don't just grab the latest run.

```bash
gh run list --workflow=build.yml --branch=<current-branch> --limit=5
```

If no run matches the SHA:
- `git log origin/<branch>..HEAD` shows unpushed commits → tell user to
  push first.
- Otherwise the run is likely queued — wait ~15s, re-list.

If the run is **in_progress**, poll up to 3 times (~15s apart), showing
current job status each time.

### Read results

```bash
gh run view <run-id> --verbose
```

**Build job** — always present. Look for: Docker build failures, missing
deps, compile errors, registry auth issues.

**Deploy job** — only present on deploy-eligible branches. Look for: GitOps
errors, env config issues, permission failures. If absent, that's expected
— tell the user deploys only run from `<deploy-branch>`.

On failure, get the logs:

```bash
gh run view <run-id> --log-failed
```

Summarize: which job (show job URL), which step, key error lines.
Include the branch the CI run executed on (from the run's `headBranch` field).
If the CI run's branch differs from the user's current local branch, note the
mismatch in the summary.

## Step 3: Check runtime logs

Read [references/runtime-logs.md](references/runtime-logs.md) and follow
the Datadog diagnostic procedure.

## Step 4: Summarize and offer help

Read [references/common-failures.md](references/common-failures.md) for
diagnostic context when interpreting results.

Only include sections for what was investigated. Use this structure:

```
## Debug Summary

**Repo**: <owner/repo>
**Branch**: <branch>
**Commit**: <sha>

### CI Pipeline
- CI Branch: <branch the run executed on — note mismatch if differs from local>
- Build: <pass/fail — details if failed>
- Deploy: <pass/fail/skipped — details>

### Runtime (Datadog)
- <error summary, "No errors found", or "Datadog unavailable">
```

Before offering to fix runtime errors, compare the current branch (from
Step 1) to `deploy_branch` (from Step 1). If they differ, warn the user
(e.g., "You're on `<current-branch>` but the deploy ran from
`<deploy_branch>`. Switch to `<deploy_branch>` before applying fixes.").
This is a warning, not a hard block — the diagnostic summary still proceeds.

`[SIGNAL]` — when errors are found, explain the likely cause and offer to
help fix. Let the user decide whether to proceed.

## Gotchas

- ALWAYS match CI runs by HEAD commit SHA — never grab the latest run blindly.
- NEVER assume Datadog MCP is available — always handle the unavailable case gracefully.
- IF the build workflow file is missing or unparseable, fall back to the repo name for service name.
- NEVER skip the intent classification step — running all paths wastes context and confuses the summary.
- IF no deploy job exists for the current branch, explain that deploys only run from the deploy branch — don't report it as a failure.
- ALWAYS check branch context before offering to fix runtime errors — applying fixes on the wrong branch creates drift.

## When NOT to use this skill

- Executing a spec → `agent-coding` skill
- Creating or researching a spec → `create-spec` skill
- Reviewing an agent-authored PR → `pr-review` skill
- Setting up a new repo → `repo-setup` skill
- Curating learnings → `spec-retro` skill

## Reference

- [references/runtime-logs.md](references/runtime-logs.md) — Datadog search
  queries, surrounding log fetch, aggregation patterns
- [references/common-failures.md](references/common-failures.md) — Symptom →
  cause → location lookup table
- [references/user-profile.md](references/user-profile.md) — Optional local
  user profile schema, mode definitions, and tag behavior
- [references/agent-tags.md](references/agent-tags.md) — Five-tier tag
  behavior grid and signal-gated escalation rules
