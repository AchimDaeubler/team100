# Dimension Review — Inline Path

Applied from `.cursor/skills/pr-review/SKILL.md` **Step 3B**. The main
agent walks the five dimension signal tables directly instead of
dispatching subagents. This path services three callers:

1. **Full inline pass** — subagent dispatch is unavailable at this site.
2. **Per-lane fallback** — a single dispatched lane failed (AC-7);
   cover that one dimension using its table below while the other four
   keep their dispatch results.
3. **Opt-out hook** — a future gate on the Step 3 stub can route the
   entire dimension pass here without modifying this reference.

Produce the same per-dimension verdict shape as Step 3A: **pass**,
**flag**, or **fail** with severity-tagged findings (`blocking` vs.
`advisory`). Severity maps to the verdict the same way as the dispatch
path: `blocking` → `fail`, `advisory` → `flag`, no findings → `pass`.

Record findings against the signal rows from
[../assets/review-checklist.md](../assets/review-checklist.md) — that
checklist is the single source of truth for signal wording; do not
paraphrase.

## Dimension 1 — Spec compliance

Does the PR satisfy every acceptance criterion?

| Signal | Pass | Fail |
|--------|------|------|
| AC coverage | Every AC has a corresponding change with observable evidence | ACs are claimed as met with no supporting change |
| Measurement fidelity | Verification method matches what the AC actually asks for | Agent redefined what "meets" means (see anti-gaming) |
| Completeness | All ACs addressed — none silently dropped | Missing ACs with no waiver rationale |

## Dimension 2 — Scope drift

Does the PR stay within the spec's boundaries?

| Signal | Pass | Fail |
|--------|------|------|
| File boundary | Only files in "likely affected" are touched | Files under "NOT to modify" are changed |
| Functional boundary | Changes serve an AC or are necessary scaffolding | New behavior beyond any AC (feature creep) |
| Dependency boundary | No new libraries, services, or APIs unless spec allows | Unmentioned dependencies introduced |

## Dimension 3 — Test coverage

Are changes verified?

| Signal | Pass | Fail |
|--------|------|------|
| New behavior tested | New functionality has corresponding tests | Tests are absent or trivially tautological |
| Existing tests pass | No regressions introduced | Tests modified to pass rather than fixing code |
| Edge cases | Boundary conditions and error paths covered | Only happy path tested |

For markdown/config-only specs (like skill files), this dimension is
evaluated as: "Can someone follow the output without additional
guidance?" Mark `N/A` only when the spec explicitly states no automated
tests.

## Dimension 4 — Security surface

Does the PR avoid introducing vulnerabilities?

| Signal | Pass | Fail |
|--------|------|------|
| Secrets | No hardcoded credentials, tokens, or keys | Secrets in code or config committed |
| Input handling | User input validated/sanitized | Raw input passed to queries, commands, or templates |
| Permissions | Access controls unchanged or intentionally modified | Authorization checks removed or weakened |

For non-code PRs (markdown, config), confirm no secrets are embedded
and mark remaining signals `N/A`.

## Dimension 5 — Approach quality

Is the implementation well-crafted?

| Signal | Pass | Fail |
|--------|------|------|
| Pattern conformance | Follows patterns named in implementation guidance | Invents new patterns when established ones exist |
| Simplicity | Solution complexity matches problem complexity | Over-engineered or unnecessarily abstract |
| Readability | Code is clear without excessive comments | Dense, clever, or poorly structured |
| Skill file size | SKILL.md under 250 lines (soft) / 400 lines (hard) | SKILL.md exceeds limits without extraction to `references/` |

## Feeding the synthesis step

Per-lane-fallback callers attach their inline result to the dispatched
results and note the fallback explicitly in the verdict. Full-inline
callers hand all five verdicts directly to `SKILL.md` synthesis, which
still applies the four synthesis responsibilities — dedupe, severity
re-rank, N/A reconciliation, hand-off to Step 4 — even when no
cross-lane duplication occurred. The verdict format does not change
between paths.
