---
name: repo-setup
description: >
  Set up a product repo for the Creator process. Scaffolds .spec/ directory,
  baseline .cursor/rules/, CI readiness checklist, trunk-based branching
  validation, and checks Creator skill availability. Use when the user says
  "set up this repo for the Creator process" or needs to onboard a repo.
---

# Repo Setup

Brings a product repo to "Creator-ready" state — the minimum scaffolding
required before spec-driven, agent-executed work can begin.

## Prerequisites

Apply [references/dependency-preflight.md](references/dependency-preflight.md)
before Step 1. Run all checks and present a consolidated report.

| Dependency | Type | Purpose |
|------------|------|---------|
| `git` | Required | Repo assessment, branching validation, commits |

If `git` is missing, stop with the error report.

## Optional user profile

Apply [references/user-profile.md](references/user-profile.md) before Step 1. Per-user, not part of repo readiness.
- Mode governs tag behavior and explanation depth. Prefer `.spec/.gitignore` for `user-config.yaml`.
- `[GATE]` supplement vs baseline, final write. `[CHECK]` skill availability unknown.

**Creator-ready means:**
1. `.spec/` directory exists
2. `.cursor/rules/` exists with baseline repo instructions
3. CI covers type check, lint, tests, and security scan
4. Trunk-based branching is configured
5. Required Creator skills are available in the current session (at minimum:
   `create-spec`)

## Workflow

Follow these steps in order. The skill is idempotent — running it on an
already-configured repo validates without overwriting.

### Step 1: Assess current state

Before making any changes, survey the repo:

1. Check if `.spec/` directory exists
2. Check if `.cursor/rules/` directory exists and contains rule files
3. Identify the default branch (`main` or `master`)
4. Check for CI configuration files (`.github/workflows/`, `Jenkinsfile`,
   `.gitlab-ci.yml`, `azure-pipelines.yml`, etc.)
5. Check the agent's accessible skill inventory for required Creator skills
   (`create-spec` at minimum)

Do NOT infer current-session skill availability from file paths or string
matching. If the runtime context does not expose the accessible skill
inventory, report the skill state as unknown and ask the user how to proceed.

Report findings to the user as a checklist:
```
Creator-ready checklist:
  [x] .spec/ directory
  [ ] .cursor/rules/ with repo instructions
  [x] CI pipeline configured
  [x] Trunk-based branching (default branch: main)
  [x] Creator skills available to this agent (`create-spec`)
```

If runtime skill availability is unknown, say so explicitly (for example:
`[?] Creator skills available to this agent — runtime inventory not exposed`)
and ask the user whether to proceed.

### Step 2: Scaffold `.spec/` directory

If `.spec/` does not exist, create it with a `.gitkeep` file and a colocated
`.gitignore` for the optional local user profile:
```
.spec/
├── .gitignore
└── .gitkeep
```

Use `.spec/.gitignore` to ignore `user-config.yaml` so the local-only profile
rule stays scoped to `.spec/` instead of the repo root.

If `.spec/` already exists, confirm it and preserve any existing `.spec/.gitignore`
content rather than overwriting it.

### Step 3: Set up `.cursor/rules/`

**IF** `.cursor/rules/` already has content, show the user the baseline
template and ask if they want to supplement their existing rules. Otherwise:

`[GATE]` the supplement decision and the final write approval.

1. Read the baseline template at `assets/templates/cursor-rules-baseline.md`
2. Gather context — scan the repo for file extensions, config files
   (`package.json`, `pyproject.toml`, `go.mod`, etc.), README content, and
   git history. Note anything that hints at the intended stack.
3. **For greenfield repos** (no source code, no dependency files): have the
   tech-stack discussion *before* writing any rules content. Ask the user
   what the project is for and what stack they intend to use. Do NOT write
   the file first and review after.
4. Walk through every `[PLACEHOLDER]` section in the template
   conversationally. For each placeholder:
   - Suggest a concrete value, drawing on the context gathered in sub-step 2
     and the hint text inside the placeholder markers
   - Explain trade-offs briefly in plain language
   - Confirm the value or adjust based on the user's response
   - Cover all sections: Project Overview, Naming, Error handling, File
     organization, Test expectations, and Dependencies
5. After all sections are discussed, present a single summary of every
   proposed value and ask for final approval before writing the file.
6. Write `.cursor/rules/repo-instructions.md` with the confirmed values.
   Every `[PLACEHOLDER]` must be replaced with a concrete value — never
   write deferred text like "TBD", "Not yet decided", or "None established
   yet". If the user explicitly wants to defer a decision after seeing
   alternatives, record it as a clear follow-up action (e.g., "Decide
   primary framework — revisit after prototyping") rather than a silent
   blank.

### Step 4: Scaffold development environment (optional)

After the tech stack is agreed in Step 3, offer to set up the local
development environment. If the user declines, skip to Step 5.

1. Create foundational project files based on the decisions in
   `repo-instructions.md` — dependency manifest, linter/formatter config,
   `.gitignore`, and source/test directory stubs consistent with the
   agreed file organization
2. Explain each file as you create it — what it does and why. This is a
   teaching moment for less technical users, not a black box
3. Run a smoke check: install dependencies, run the linter, run the test
   runner. Report whether the environment is functional or what failed

### Step 5: CI readiness check

1. Read the checklist at `assets/templates/ci-checklist.md`
2. Walk through each item with the user, checking their CI configuration
3. If Step 4 scaffolded the environment, reference the specific tools that
   are installed (e.g., "You have Ruff configured — add `ruff check .` to
   CI") rather than speaking hypothetically about tool choices
4. For any gaps, provide guidance on what to add (but do NOT write CI config
   files — too many CI systems to support generically)
5. Record the results so the user has a clear list of follow-up items

### Step 6: Validate trunk-based branching

1. Confirm the default branch exists and is the merge target for feature
   branches
2. Confirm there are no long-lived feature branches (or flag them)
3. Provide branch protection guidance:
   - Require PR reviews before merge
   - Require CI to pass before merge
   - Prevent direct pushes to default branch
   - These are platform-specific (GitHub, GitLab, etc.) — provide as
     recommendations, not automation

### Step 7: Clarify skill access constraints

`[CHECK]` — skill availability unknown requires user input.

Do NOT copy Creator skills into the target repo as part of repo setup.

If the required skills are available to this agent, tell the user the workflow
can proceed in the current session.

If the required skills are unavailable, explain that the repo is not yet
Creator-ready for agent execution, and that the longer-term distribution or
access model remains an open operational question outside this skill.

If skill availability is unknown, say so explicitly and ask the user whether to
continue with the rest of the scaffolding despite the unresolved access state.

### Step 8: Commit scaffolding

Commit all scaffolded files to the default branch — follow
[Git operations](references/lifecycle.md#git-operations). Use type `chore`
with the unscoped format because repo setup has no active spec
(e.g., `chore: scaffold Creator process files`).

### Step 9: Summary and next steps

Re-present the Step 1 checklist with updated results. If required Creator
skills are available to this agent, tell the user the repo is Creator-ready for
this session, then treat repo setup as a bounded handoff point:

- If the user asks a broad "what next?" or roadmap-style follow-up, do NOT
  produce one giant multi-phase plan as the primary artifact
- Decompose the work into a short ordered backlog of spec-sized candidates
  instead, and say that specs remain the unit of work
- Steer the user to one bounded next slice and recommend a fresh session for
  creating it, for example: "You're at a clean handoff point. Start a fresh
  session and ask me to create a spec for the first slice"

If skill access is unavailable or unknown, do NOT say the repo is
Creator-ready; explain that skill access remains unresolved.

## Gotchas

- NEVER overwrite existing `.cursor/rules/` or `.spec/` entries — check first, confirm with the user, add only what's missing.
- NEVER write CI config files — provide gap analysis and recommendations only.
- ALWAYS provide branch protection as principles (require reviews, require CI, block direct pushes) — platform-specific configuration is the user's responsibility.
- ALWAYS customize the baseline rules template — it is a starting point, not a final product.
- NEVER copy Creator skills into the target repo — surface missing skill access directly.
- ALWAYS end with a bounded handoff — one next spec-sized slice or a short backlog, not an indefinite roadmap session.

## When NOT to use this skill

- Creating a spec in an already-configured repo → `create-spec` skill
- Executing code against an existing spec → `agent-coding` skill
- Reviewing an agent-authored PR → `pr-review` skill

## Reference

- [references/lifecycle.md](references/lifecycle.md) — Spec lifecycle states
  and transitions (for explaining the process to new teams)
- [references/user-profile.md](references/user-profile.md) — Optional local user
  profile schema, mode definitions, and tag behavior
