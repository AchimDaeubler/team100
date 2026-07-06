# Curation Workflow (Steps 6–7)

Apply curation decisions and run retention review. Used in both single-spec
retro and multi-spec sweep modes.

## Step 6: Apply curation decisions (both modes)

Four common outcomes, in order of frequency:

`[SIGNAL]` learning improvements, ledger curation decisions, and promotion
approvals — auto-proceed when all recommendations are straightforward
promotions/refinements with no contradictions, complex merges, or stale
conflicts; escalate when a concern is flagged. `[GATE]` rebuild replacements
(destructive, explicit request only). `[CHECK]` the human-facing docs pass.

| Outcome | When | Format |
|---------|------|--------|
| New `.spec/_ledger/{domain}.yaml` entry | Durable learning applies across specs in a domain and is not already captured | YAML ([template](../assets/ledger-entry-template.yaml)) |
| Existing ledger entry refinement | The durable learning already exists but the curated entry needs better wording/context, tag cleanup, merge handling, or stale marking | YAML update in the existing ledger file |
| `.cursor/rules/` | Learning should influence all future agent work | Cursor rule file (markdown) |
| README or repo docs | Learning is relevant to human developers | Documentation update |

If the best outcome is "keep it spec-local," leave the learning in the source
spec's `meta.yaml` and explicitly say why it stays local or awaits later
corroboration.

**New ledger entry:**

1. Determine the domain from the learning's tags and context. The primary tag
   cluster names the domain (e.g., tags `[agent-coding, stop-points]` →
   `agent-coding.yaml`). Create new domain files as needed.
2. Add the entry using the ledger schema: same fields as `meta.yaml` learnings
   (`type`, `summary`, `context`, `tags`, `date`) plus `source_spec` for
   traceability. See [ledger-entry-template.yaml](../assets/ledger-entry-template.yaml).
3. Commit the ledger update separately — see
   [Git operations](lifecycle.md#git-operations).

**Existing ledger refinement:**

1. Edit the current entry when new evidence improves its summary, context, or
   tags without changing the underlying lesson.
2. When entries overlap, keep the clearest surviving entry, fold in missing
   context, and preserve traceability by marking redundant or contradicted
   entries `stale: true` with `stale_reason` instead of silently deleting them
   when history should remain visible.
3. When Step 5c was used, write the reviewed candidate ledger files only after
   the user's explicit confirmation. Treat that replacement as a curated ledger
   update, and rely on git history for reversal if needed.
4. Commit the ledger refinement separately — see
   [Git operations](lifecycle.md#git-operations).

**Rules promotion:** Draft a rule capturing the learning as an agent
instruction. Add to an existing or new file in `.cursor/rules/`. Commit per
[Git operations](lifecycle.md#git-operations).

**Docs promotion:**

1. Do a lightweight scan for the repo's core human-facing docs before deciding
   no update is needed:
   - top-level `README.md`
   - top-level status/plan docs such as `ROADMAP.md`, `STATUS.md`, or an
     equivalent current-state/next-steps doc
   - architecture or onboarding docs in common locations such as the repo root
     or `docs/` when present
2. Review those docs against the completed work. Ask whether it changes setup
   or use instructions, current repo state, delivered scope, architecture
   direction, or recommended next work.
3. Keep this pass separate from `.spec/_ledger/` and `.cursor/rules/`.
   Agent-facing promotions are not substitutes for human-facing docs review.
4. Either:
   - name the doc(s) to update and make the change
   - or explicitly report which core docs were reviewed and why no change was
     needed
5. Commit per [Git operations](lifecycle.md#git-operations).

Each ledger/rules/docs change is a separate commit for clean history and easy
reversion. The target branch depends on the retro mode:

- **Single-spec retro (auto-chained or standalone, branch exists):** Commit on
  the current implementation branch (`SPEC-*`). These commits appear on the
  spec's open PR alongside the implementation.
- **Single-spec retro (deferred, branch gone):** Commit on the `retro-SPEC-{n}`
  branch created in Step 2. Push and open a PR after all curation completes.
- **Multi-spec sweep:** Commit on the `retro-{slug}` branch created in Step 2.
  Push and open a PR after all curation completes.

**After applying ledger or rules changes**, still run the human-facing docs pass
above. The ledger and rules are agent-facing; README and repo docs are
human-facing. If a learning changes how humans should set up, use, or reason
about the project, propose a docs promotion. If no docs change is needed,
explicitly say which core docs were reviewed and why they were unaffected.

## Step 7: Retention and curation review (both modes)

Review the ledger for curation targets, not just stale entries. An entry may
need action when:

| Signal | Example |
|--------|---------|
| **Thin wording or missing context** | Summary is too terse to use without reopening the source spec |
| **Tag drift** | Nearby entries use inconsistent tags such as `git-worktree` vs `worktree` |
| **Duplicate overlap** | Two ledger entries capture the same durable lesson |
| **Superseded spec** | A newer spec solved the same problem differently |
| **Codebase change** | The code the learning references has been refactored or removed |
| **Architectural shift** | A decision learning references an approach that was replaced |
| **Contradiction** | A newer learning directly contradicts an older one |

For entries that need curation:

1. Refine summary/context or normalize tags in place when the lesson still
   stands but the entry is hard to discover or understand.
2. Merge overlapping entries by keeping the clearest entry, folding in missing
   context, and marking the redundant entry `stale: true` with `stale_reason`
   when you need to preserve traceability.
3. For stale or contradicted entries, add `stale: true` and `stale_reason`.
   Do NOT delete them just to clean up the file.
4. Commit per [Git operations](lifecycle.md#git-operations).

If the ledger doesn't exist yet or has few entries, skip this step. If the user
explicitly wants a clean reconstruction instead of incremental cleanup, use
Step 5c.
