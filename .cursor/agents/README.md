# Creator Kit Subagent Convention

Project-local subagents in this directory are narrow evidence-gathering lanes.
The parent agent owns orchestration, synthesis, and any approval-gated
interaction with the user.

Two lane families live here:

- **Research lanes** for `create-spec`'s research gate — `learnings-curator`,
  `repo-analyst`, `docs-researcher`, `prior-art-researcher`.
- **Review lanes** for `pr-review`'s Step 3A dispatch path —
  `spec-compliance-reviewer`, `scope-drift-reviewer`,
  `test-coverage-reviewer`, `security-surface-reviewer`,
  `approach-quality-reviewer`.

## Frontmatter

Each Creator Kit subagent should declare:

- `name`
- `description`
- `model`
- `readonly: true`
- `is_background: true`

Default to `model: fast` for search-heavy lanes. If a lane repeatedly needs
deeper reasoning, change that file's `model` value directly rather than adding
parallel workflow machinery.

## Lane pattern

Each agent file should include these sections:

1. `How you differ from the other ... lanes`
2. `What you receive`
3. `What you do` or `What you check`
4. `How to report`
5. `Rules`

## Input contract

The parent agent should pass lane-specific prompts that include:

- Spec identity: `id`, `title`, `category`
- Problem statement and any relevant acceptance criteria
- Repo, domain, and stack context already known
- Likely files, technologies, related specs, or keywords if already identified
- Any explicit lane exclusions so the subagent stays in its lane

## Output contract

Return a structured lane result using this shape:

- `Status`: `USEFUL` | `LIMITED` | `NO-SIGNAL`
- `Summary`: one-sentence takeaway
- `Findings`: ranked findings with evidence and relevance reasoning
- `Open questions / risks`: only when signal exists
- `Fallback note`: missing tools, weak signal, or why the lane stayed limited

## Grounding rules

- Ground every finding in explicit evidence.
- Use repo-root-relative file paths for repo-local claims.
- Use ledger entry identifiers or `.spec/.../meta.yaml` references for prior
  learnings.
- Use authoritative docs URLs for documentation claims when available.
- Name the source or source type for prior-art claims.
- Prefer fewer high-signal findings over exhaustive noisy lists.
- Do not synthesize across lanes or write the final spec sections; the parent
  agent does that.
- Do not manufacture findings when evidence is weak. Return `LIMITED` or
  `NO-SIGNAL` instead.
- Keep approval-gated decisions with the parent agent. Subagents can rank
  candidates, but the parent agent owns user-facing curation or sign-off.
