# Repo Instructions

Baseline rules for agent-first development. Customize each section for your
project — look for `[PLACEHOLDER]` markers.

## Project overview

- **Name:** [PLACEHOLDER — project name]
- **Description:** [PLACEHOLDER — one-line description of what this project does]
- **Primary language:** [PLACEHOLDER — common: Python, TypeScript, Go, Java, Rust, C#]
- **Framework:** [PLACEHOLDER — common: Next.js, Django, FastAPI, Spring Boot, Flask, Express, none]
- **Package manager:** [PLACEHOLDER — common: uv, pip, npm, pnpm, yarn, maven, cargo, go modules]

## Coding conventions

### Style and formatting

- Follow the existing code style in the repo — consistency over personal
  preference.
- Use the project's configured formatter (Prettier, Black, gofmt, etc.)
  before committing.
- Prefer explicit over clever. Code should be readable without comments
  explaining what it does.

### Naming

- Use descriptive names that reveal intent.
- [PLACEHOLDER — naming conventions: e.g., "camelCase for variables,
  PascalCase for types" (TS/Java), "snake_case for functions and variables,
  PascalCase for classes" (Python/Rust)]

### Error handling

- Never swallow errors silently.
- Use the project's established error handling patterns.
- [PLACEHOLDER — error handling approach: e.g., "use Result types" (Rust/Go),
  "raise typed exceptions with context" (Python/Java), "return error codes",
  "use custom error classes extending Error" (TS/JS)]

## File organization

- [PLACEHOLDER — directory structure: e.g., "src/ for source, tests/ mirroring
  src/", "app/ with routes/, models/, services/", "pkg/ for library code,
  cmd/ for entry points" (Go), "src/components/, src/hooks/, src/utils/" (React)]
- Keep files focused — one module/class/component per file unless there's a
  strong reason to co-locate.
- Test files live [PLACEHOLDER — common: "next to source files as
  *.test.ts" (JS/TS), "in a parallel tests/ directory" (Python/Java/Go)].

## Commit message format

Use these defaults for Creator-managed commits:

```
Spec-driven work:
<type>(SPEC-<n>): <short summary>

Non-spec workflows:
<type>: <short summary>

<optional body explaining why, not what>
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`

These six types are a **closed set** for this project. The Conventional Commits
spec only mandates `feat` and `fix`; all other types are optional and
project-defined. A small, purpose-driven list reduces classification ambiguity
and keeps type-based filtering useful.

#### Excluded Conventional Commit types

| Standard CC type | Mapping | Rationale |
|------------------|---------|-----------|
| `perf` | `refactor` (or `fix` if correcting a perf bug) | Performance improvement without behavior change is a refactor |
| `build` | `chore` | Build system and dependency changes are maintenance |
| `ci` | `chore` | CI pipeline changes are maintenance |
| `style` | `chore` | Formatting-only changes are maintenance |
| `revert` | Use the type of the original commit being undone (fallback: `chore`) | Reverts undo a prior change; classify by the original purpose |

#### Lifecycle artifact commits

Commits that touch spec metadata, ledger entries, or similar lifecycle artifacts
use existing types — classify by purpose, not by file:

| Artifact | Example commit | Type rationale |
|----------|----------------|----------------|
| Spec status transition | `docs(SPEC-013): transition to done` | Documenting lifecycle state |
| Ledger promotion | `docs(SPEC-013): promote user profile guidance` | Reference content promotion |
| Retro curation | `docs(SPEC-013): curate learnings` | Reference content update |
| Rule or skill behavior change | `refactor(SPEC-013): extract mode references` | Alters agent behavior |

Do not invent ad-hoc types like `spec:`, `ledger:`, or `retro:`.

#### Squash-merge commits

When a PR is squash-merged, the resulting commit on the default branch follows
the **PR title format** (`SPEC-<n>: <short title>`), not the per-commit format.
This is by design — squash-merge commits represent the merged unit of work, and
the hosting platform derives their message from the PR title. Individual commit
messages from the feature branch are preserved in the squash commit body.

Choose the type from the primary effect of the change, not from the file
extension:

- Use `feat`, `fix`, `refactor`, or `chore` for markdown-based rules, prompts,
  specs, runbooks, or workflow guidance when the change alters behavior,
  defaults, operational steps, or other expected outcomes.
- Use `docs` only when the change is primarily explanatory or reference content
  and does not change expected behavior or workflow outcomes.
- Use `test` when the primary purpose is adding or adjusting verification.
- If a change both updates behavior and explains it, prefer the
  behavior-driving type.

Use the current or source spec ID as the scope for spec-driven work. Do not
invent placeholder or fake `SPEC-*` scopes when no active or source spec
exists.

Examples:
- `feat(SPEC-013): add capability-aware user profiles`
- `fix(SPEC-013): correct workflow default selection guidance`
- `docs(SPEC-013): link SPEC-013 PR`
- `chore: scaffold Creator process files`

## PR title format

Use these defaults for Creator-managed pull requests:

```
Single-spec PRs:
SPEC-<n>: <short title from the spec>

Non-spec or multi-spec PRs:
<descriptive title without a SPEC-* prefix>
```

Derive the title from the spec's `title` field — do not invent new wording.
Do not use placeholder or fake `SPEC-*` prefixes for PRs that are not
single-spec work.

Examples:
- `SPEC-013: Add capability-aware user profiles`
- `Scaffold Creator process files` (non-spec)

## Test expectations

- Every new feature or bug fix should include tests.
- [PLACEHOLDER — test tooling: e.g., "unit tests with pytest" (Python),
  "unit tests with Jest/Vitest" (TS/JS), "go test" (Go), "JUnit" (Java),
  "e2e tests with Playwright/Cypress"]
- Tests should be independent and not rely on execution order.
- Use descriptive test names that explain the scenario and expected outcome.
- [PLACEHOLDER — coverage thresholds if applicable: e.g., "maintain >80%
  line coverage", "no coverage requirement yet", "enforce on CI"]

## Dependencies

- Prefer well-maintained, widely-used libraries over custom solutions.
- Pin dependency versions for reproducibility.
- [PLACEHOLDER — dependency policy: e.g., "prefer stdlib over third-party",
  "security review required for new deps", "pin exact versions in lockfile"]

## Agent-specific guidance

- Always read existing code before writing new code. Check for established
  patterns before introducing new ones.
- Do not refactor code outside the scope of the current spec.
- When a spec lists "files NOT to modify", respect that boundary strictly.
- Prefer small, focused commits over large monolithic changes.
