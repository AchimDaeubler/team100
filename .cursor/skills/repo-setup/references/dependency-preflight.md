<!-- Shared reference: canonical source is `.cursor/skills/_shared/dependency-preflight.md`. Edit there, then run `./sync.sh`; do not hand-edit copied `references/` files. -->

# Dependency Preflight

Upfront validation pattern for Creator skills. Check all dependencies before
starting work — fail fast and fail clear.

## Severity tiers

| Tier | Behavior |
|------|----------|
| **Required** | Missing → stop execution with an actionable error. No partial work, no "note and continue." |
| **Optional** | Missing → warn with the specific capability lost. Ask the user whether to proceed in degraded mode or stop to fix the dependency. Never silently skip. |

## CLI tool checks

Verify tools at the start of the skill workflow, before any state transitions
or implementation work.

**PowerShell:** `Get-Command <tool> -ErrorAction SilentlyContinue`
**Bash:** `command -v <tool> >/dev/null 2>&1`

Run every check regardless of earlier failures, then present a consolidated
report (doctor-style). Do not stop on the first failure — users prefer seeing
everything wrong in one pass.

### Known CLI dependencies

| Tool | Skills | Severity | Degradation if absent |
|------|--------|----------|-----------------------|
| `git` | All | Required | No skill can operate without version control |
| `gh` | agent-coding | Required | PR creation in completion workflow cannot proceed |
| `gh` | create-spec | Optional | ID allocation falls back to local-only scan; number may collide with concurrent users |
| Platform shell (bash + coreutils or PowerShell) | All with scripts | Required | Scripts cannot execute |

## MCP server checks

Three-step detection strategy:

1. **Configured?** Check if `mcps/<server-name>/` exists in the project's MCP
   folder. If absent, the server is not configured.
2. **Needs auth?** Check if the server's `tools/` folder contains an
   `mcp_auth` tool descriptor. If present, call `mcp_auth` so the user can
   authenticate before proceeding.
3. **Functional?** Attempt a lightweight tool call to confirm the server
   responds. If the call fails with an auth-related error, emit a specific
   re-authentication instruction and stop rather than retrying.

### Known MCP dependencies

| Server | Skills | Severity | Degradation if absent |
|--------|--------|----------|-----------------------|
| `cursor-ide-browser` | brainstorming | Optional | Visual companion unavailable; text-only brainstorming proceeds |
| `user-Notion` | create-spec (implicit) | Optional | Notion-sourced context unavailable; skill proceeds without it |

### MCP error differentiation

Different failure states need distinct messages and remediation:

| State | Message pattern | Remediation |
|-------|----------------|-------------|
| Not configured | "`<server>` MCP is not configured in this project." | "Add the server in Cursor MCP settings." |
| Auth required | "`<server>` MCP requires authentication." | "Authenticate in Cursor — the `mcp_auth` prompt should appear." |
| Auth expired | "`<server>` MCP authentication has expired or is invalid." | "Re-authenticate in Cursor MCP settings and restart." |
| Unresponsive | "`<server>` MCP is not responding (timeout after 10s)." | "Check that the MCP server is running and restart if needed." |

## Error message formula

Every dependency error follows the three-part structure:

1. **What's missing** — name the specific tool or server
2. **Why it's needed** — explain the workflow step that requires it
3. **How to fix** — provide the install command, URL, or action

Example (required):

> **git** is not installed. It is required for all Creator workflows (version
> control, branching, commits). Install from https://git-scm.com/downloads.

Example (optional):

> **GitHub CLI (gh)** is not installed. Without it, spec ID allocation uses a
> local-only scan that may collide with concurrent users. Install from
> https://cli.github.com/ — or proceed without remote ID claims?

## Consolidated report format

When multiple issues are found, present a single consolidated report:

```
Dependency check:
  [PASS]  git
  [FAIL]  gh — required for PR creation. Install from https://cli.github.com/
  [WARN]  cursor-ide-browser MCP — not configured; visual companion unavailable
  [PASS]  platform shell (PowerShell)

1 required dependency missing — cannot proceed.
Fix the issue above and retry.
```

- **[PASS]** — present and functional (include only when other items are
  failing, to show the full picture; silent when everything passes)
- **[FAIL]** — required dependency missing; execution stops after the report
- **[WARN]** — optional dependency missing; ask whether to proceed in degraded
  mode

If all checks pass, preflight is silent — no user-visible output.

## Skill integration

Each skill's Prerequisites section is concise (~5–10 lines):

1. A table declaring required and optional dependencies with purpose
2. An instruction to validate before the workflow begins
3. A reference to this file for check procedures and error templates

If any required dependency is missing, stop with the consolidated error
report before doing any work. If an optional dependency is missing, name the
lost capability and ask the user before proceeding in degraded mode.
