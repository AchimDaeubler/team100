# PR Review Checklist

Use this checklist during review. Copy it into the PR comment or use it as
a working artifact. Fill in the verdict column for each signal.

**PR:** _(link)_
**Spec:** _(SPEC-{n} title)_
**Reviewer:** _(name)_
**Date:** _(date)_

---

## Dimension 1 — Spec compliance

| Signal | Verdict | Evidence / Notes |
|--------|---------|------------------|
| Every AC has a corresponding change | | |
| Verification matches what the AC asks for | | |
| All ACs addressed (none silently dropped) | | |

**Dimension result:** ☐ Pass ☐ Flag ☐ Fail

## Dimension 2 — Scope drift

| Signal | Verdict | Evidence / Notes |
|--------|---------|------------------|
| Only "likely affected" files are touched | | |
| Changes serve an AC or necessary scaffolding | | |
| No unmentioned dependencies introduced | | |

**Dimension result:** ☐ Pass ☐ Flag ☐ Fail

## Dimension 3 — Test coverage

| Signal | Verdict | Evidence / Notes |
|--------|---------|------------------|
| New behavior has corresponding tests | | |
| No regressions (existing tests pass) | | |
| Edge cases and error paths covered | | |

**Dimension result:** ☐ Pass ☐ Flag ☐ Fail ☐ N/A (non-code spec)

## Dimension 4 — Security surface

| Signal | Verdict | Evidence / Notes |
|--------|---------|------------------|
| No hardcoded secrets | | |
| User input validated/sanitized | | |
| Access controls intact | | |

**Dimension result:** ☐ Pass ☐ Flag ☐ Fail ☐ N/A (non-code spec)

## Dimension 5 — Approach quality

| Signal | Verdict | Evidence / Notes |
|--------|---------|------------------|
| Follows patterns from implementation guidance | | |
| Complexity matches the problem | | |
| Code is clear and readable | | |
| Skill file size within limits (250 soft / 400 hard) | | |

**Dimension result:** ☐ Pass ☐ Flag ☐ Fail

---

## Anti-gaming checks

| Check | Clean? | Evidence / Notes |
|-------|--------|------------------|
| Measurement redefinition | | |
| Proxy evidence | | |
| Scope dismissal | | |
| Tautological tests | | |
| Silent AC omission | | |

**Anti-gaming result:** ☐ Clean ☐ Triggered

---

## Verdict

☐ **Approve** — All dimensions pass, anti-gaming clean
☐ **Request changes** — Fixable issues (list action items below)
☐ **Reject** — Fundamental problem (state rationale below)

### Action items

1.
2.
3.

### Notes

_(Any additional context, learnings discovered during review, or spec
improvement suggestions)_
