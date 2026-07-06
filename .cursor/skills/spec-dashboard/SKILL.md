---
name: spec-dashboard
description: >
  Generate, open, or remove the local spec status dashboard
  (`spec-dashboard.html`). Single entry point for every regeneration path —
  direct user request and automatic lifecycle re-entry — over the generator
  pair under `.cursor/skills/spec-dashboard/scripts/`; no new generation
  logic. Use when the user says "generate the spec dashboard", "refresh the
  spec dashboard", "show the spec dashboard", "open the spec dashboard",
  "open the dashboard in Cursor", "open the dashboard externally", "remove
  the spec dashboard", or "clean up the spec dashboard".
---

# Spec Dashboard

A small, user-facing wrapper around the dashboard generator and the sole
entry point for dashboard regeneration. Handles three direct user intents —
**generate/refresh**, **open**, and **cleanup** — and serves the same
**generate** path for automatic lifecycle re-entries from `create-spec`,
`agent-coding`, and `spec-retro`. The skill ships no new generation code —
it delegates to the canonical pair under
`.cursor/skills/spec-dashboard/scripts/`.

## Prerequisites

Apply [references/dependency-preflight.md](references/dependency-preflight.md)
before Step 1. Run all checks and present a consolidated report.

| Dependency | Type | Purpose |
|------------|------|---------|
| `git` | Required | Locate repo root, check `.gitignore`, detect tracked state |
| Platform shell (bash + coreutils or PowerShell) | Required | Invoke the existing dashboard generator and OS default opener |

If any required dependency is missing, stop with the error report before
doing any work.

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 1.
- Mode governs interaction cadence for the open-path choice; it does not
  change what the skill generates, opens, or removes.
- `[CHECK]` ambiguous open-path intent. `[SIGNAL]` gitignore auto-append,
  regeneration of a missing file. `[NOTE]` tracked-file warning, cleanup
  no-op confirmation.
- The pastable URL is emitted in every mode on every open-path run. In
  `streamlined` mode the skill additionally launches the OS default browser
  silently, without asking.

## Workflow

Follow these steps in order. Which later steps run depends on the intent
classified in Step 1.

### Step 1: Classify intent

Map the request to one of three intents. Only run the steps that match.

| Intent | Trigger phrases | Steps to run |
|--------|-----------------|--------------|
| **Generate** | "generate", "refresh", "rebuild" the (spec) dashboard | 2 → 3 |
| **Open** | "open", "show", "view" the (spec) dashboard | 2 → 3 (if missing or fresh requested) → 4 |
| **Cleanup** | "remove", "delete", "clean up" the (spec) dashboard | 5 |

Lifecycle re-entries from caller skills (`create-spec`, `agent-coding`,
`spec-retro`, and `_shared/lifecycle.md` transition bullets) activate this
skill via an "Apply the `spec-dashboard` skill to refresh the spec
dashboard" phrase. They map to the **generate** intent: run Steps 2 → 3 and
skip Steps 4 (open) and 5 (cleanup).

If the request is ambiguous, `[CHECK]` — ask once which intent applies.

### Step 2: Verify `.gitignore` coverage

Runs on every entry path that reaches Step 3 — direct user requests and
lifecycle re-entries alike — before generation. Ensures the repo-root
`.gitignore` excludes the dashboard artifact.

1. Locate the repo root with `git rev-parse --show-toplevel`.
2. Check for a line exactly matching `spec-dashboard.html` in the root
   `.gitignore` (idempotent via exact-line match — not a regex/prefix
   check). If `.gitignore` is missing, create it. If the line is absent,
   append it and `[SIGNAL]` report the change. If the line is already
   present, proceed silently.
3. Check whether the file is already tracked:

```bash
git ls-files --error-unmatch spec-dashboard.html
```

   Exit code `0` means the file is tracked; exit code `1` means untracked.
   If tracked, `[NOTE]` — surface a one-line warning recommending
   `git rm --cached spec-dashboard.html`. Do **not** modify the git index
   automatically.

Command sketches:

```bash
# bash / zsh
grep -qxF 'spec-dashboard.html' .gitignore 2>/dev/null \
  || echo 'spec-dashboard.html' >> .gitignore
```

```powershell
# PowerShell
$ignorePath = Join-Path (git rev-parse --show-toplevel) '.gitignore'
if (-not (Test-Path $ignorePath) -or
    -not (Select-String -Path $ignorePath -SimpleMatch 'spec-dashboard.html' -Quiet)) {
    Add-Content -Path $ignorePath -Value 'spec-dashboard.html' -Encoding UTF8
}
```

### Step 3: Generate the dashboard

Regenerate `spec-dashboard.html` by invoking the canonical generator (the
skill ships no new generation code): run
`.cursor/skills/spec-dashboard/scripts/dashboard.ps1` (PowerShell) or
`.cursor/skills/spec-dashboard/scripts/dashboard.sh` (bash). The script
writes to `<repo-root>/spec-dashboard.html`.

Run this step when:

- Intent is **generate/refresh**.
- Intent is **open** and `spec-dashboard.html` is missing at the repo root,
  or the user explicitly asked for a fresh copy ("open a fresh dashboard",
  "refresh then open").

For intent **open** when the file already exists and the user did not ask
for a refresh, skip this step.

### Step 4: Open the dashboard

The user always gets a **pastable URL** in a fenced code block. The OS
default browser is additionally launched based on user intent and mode.
Cursor chat does not auto-linkify `file://` URLs, so clickability is not
part of this step. The `cursor-ide-browser` MCP is also **not** used (its
runtime blocks `file://` URLs).

1. **Build the platform-correct `file://` URL** from the absolute repo-root
   path of `spec-dashboard.html`. Percent-encode spaces (`%20`), RFC 3986
   reserved characters, and literal `%` in path segments.

   - **WSL** (detect via `grep -qi microsoft /proc/version`, or
     `$WSL_DISTRO_NAME` is set): prefix `file:` to the output of
     `wslpath -m "$FILE"`. `wslpath -m` is Microsoft-documented (WSL
     release notes) as the forward-slash Windows-path form and emits
     `//wsl.localhost/<distro>/<posix-path>`; the final URL is
     `file://wsl.localhost/<distro>/<posix-path>` (single `file:` prefix).
     `$WSL_DISTRO_NAME` can compose the same URL when `wslpath` is absent
     but is not guaranteed in every process context — prefer `wslpath -m`.
   - **Linux or macOS native** (not WSL): emit `file://<absolute-posix-path>`
     — renders as `file:///home/...` or `file:///Users/...` per RFC 8089
     Appendix B.
   - **Windows native** (no WSL): emit `file:///C:/...` with forward
     slashes and a drive letter.

   ```bash
   # WSL (bash / zsh)
   URL="file:$(wslpath -m "$FILE")"
   # native POSIX
   URL="file://${FILE}"
   ```

   ```powershell
   # Windows native
   $url = 'file:///' + ($FILE -replace '\\','/')
   ```

2. **Emit the pastable URL** in a fenced code block — three backticks, the
   URL alone on its own line, three backticks, no language tag. This is
   printed on **every** open-path invocation in **every** mode, regardless
   of whether Step 3 below also launches the OS default browser. The fence
   gives Cursor chat its click-to-copy affordance; the user pastes the URL
   into their browser of choice (external browser or Cursor's Integrated
   Browser).

3. **Decide whether to also launch the OS default browser:**

| User intent | Mode | Launch? |
|-------------|------|---------|
| "open externally" / "open in my browser" | any | yes |
| "give me the URL" / "I'll open it myself" | any | no |
| "open the dashboard" (unspecified) | `streamlined` | yes, silently |
| "open the dashboard" (unspecified) | `expert` | ask once |
| "open the dashboard" (unspecified) | `guided` / `safe-auto` | `[CHECK]` — ask once |

   When launching, invoke the OS default browser. On Linux and macOS pass
   the absolute path or the `file://` URL; on Windows pass a plain path to
   `Start-Process` (it accepts paths, not URI strings):

   - Linux: `xdg-open "$FILE"` (on WSL, prefer `wslview` when available —
     `xdg-open` reliability varies on minimal setups)
   - macOS: `open "$FILE"`
   - Windows PowerShell: `Start-Process "$FILE"`

   Quote paths that contain spaces. If the launcher exits non-zero, report
   the specific error — the pastable URL from step 2 is already on screen,
   so the user still has a working path forward.

### Step 5: Clean up the dashboard

When the intent is **cleanup**, remove `spec-dashboard.html` if it exists at
the repo root. Treat a missing file as a no-op (not an error).

```bash
# bash / zsh
rm -f "$(git rev-parse --show-toplevel)/spec-dashboard.html"
```

```powershell
# PowerShell
$dash = Join-Path (git rev-parse --show-toplevel) 'spec-dashboard.html'
if (Test-Path $dash) { Remove-Item $dash -Force }
```

Report whether anything was removed. `[NOTE]` — if the file was already
missing, confirm there was nothing to clean up.

Do not run Step 2's `.gitignore` verification during cleanup — the rule
stays in place regardless of whether the artifact is currently on disk.

## Gotchas

- NEVER reimplement generation inside this skill — always invoke `scripts/dashboard.ps1` / `scripts/dashboard.sh`. Divergent path resolution or YAML extraction will drift from the real generator.
- NEVER use the `cursor-ide-browser` MCP for opening — it blocks `file://` URLs at call time. Emit the pastable URL instead.
- NEVER frame a `file://` URL as "click the link to open" — Cursor chat does not auto-linkify `file://` in any form (POSIX, WSL UNC, markdown-wrapped, bare). Present it only as a pastable URL in a fenced code block.
- NEVER emit a POSIX `file:///home/…` URL on WSL hosts — Windows-side browsers (including Cursor's Integrated Browser) cannot resolve Linux-side paths. Use `file://wsl.localhost/<distro>/…` built via `wslpath -m`.
- NEVER modify the git index automatically if `spec-dashboard.html` is tracked — warn and recommend `git rm --cached spec-dashboard.html` only.
- ALWAYS use RFC 3986 percent-encoding (`%20` for spaces, etc.) in the pastable URL and any launcher invocation that takes a URL.
- ALWAYS check `.gitignore` with an exact-line match, not a substring/regex match — idempotent re-runs must not append duplicates.
- IF the user asks to "open the dashboard" without specifying a path AND mode is `streamlined`, THEN launch the OS default browser silently and still emit the pastable URL block — do not ask which path to use.
- IF `xdg-open` fails on a WSL or minimal Linux host, THEN try `wslview` (WSL) and report the launcher failure — the pastable URL already on screen is the fallback.

## When NOT to use this skill

- Creating or researching a spec → `create-spec` skill
- Executing a spec → `agent-coding` skill
- Curating learnings across specs → `spec-retro` skill
- Reviewing an agent-authored PR → `pr-review` skill
- Configuring the per-user Creator profile → `user-setup` skill

## Reference

- [references/user-profile.md](references/user-profile.md) — Optional local
  user profile schema, mode definitions, and tag behavior
- [references/dependency-preflight.md](references/dependency-preflight.md) —
  Dependency check procedure and error templates
- [references/agent-tags.md](references/agent-tags.md) — Five-tier tag
  behavior grid and signal-gated escalation rules
