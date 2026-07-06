# Multi-Spec Sweep (Steps 3b–5c)

Periodic cross-spec review for finding cross-cutting patterns, duplicates,
contradictions, and curation targets across multiple completed specs.

**Branch context:** Create a `retro-{slug}` branch from `origin/HEAD` before
committing any curation outputs (e.g., `retro-april-sweep`). All sweep
promotion commits (ledger, rules, docs) land on this branch. After all
curation steps complete, push the branch and open a PR. See spec-retro Step 2
for full branch-context rules.

## Step 3b: Group and analyze

1. **Group by tags:** Cluster learnings sharing tags. Overlapping tags across
   specs indicate cross-cutting concerns (e.g., `[git, wsl]` → platform theme).
2. **Group by type:** Same type across specs reveals systemic issues (e.g.,
   multiple `assumption_invalidated` about the same subsystem).
3. **Review the current ledger as a curation surface:** Note entries that should
   be refined, tag-normalized, merged/superseded, or checked for staleness
   while you evaluate new learnings.

## Step 4b: Identify overlap, contradictions, and curation targets

- **Raw duplicates:** Learnings from different specs that capture the same
  insight. Keep the highest-quality version; use the others as supporting
  evidence or stale/superseded context as needed.
- **Ledger overlap:** Raw learnings or existing ledger entries that capture the
  same durable idea. Prefer refining or merging the existing entry instead of
  adding a new duplicate. Only leave it alone when the current entry is already
  clear, current, and sufficient.
- **Contradictions:** Learnings or ledger entries that assert conflicting things
  (e.g., one says symlinks work, another says they don't). Flag both sources
  for resolution — the user decides which is current.

## Step 5b: Produce curated summary

Present a structured summary:

1. **New promotion candidates** — corroborated learnings not yet in the ledger
2. **Existing entry refinements** — ledger entries that need clearer wording,
   more context, or tag normalization
3. **Merge / supersede recommendations** — overlapping raw or ledger entries and
   which entry should survive as the curated version
4. **Contradictions / stale candidates** — entries that may no longer apply or
   now conflict with newer learnings
5. **Useful but local learnings** — learnings worth keeping in spec-local
   history until later corroboration rather than promoting now

This is the preferred path for repeated patterns or cross-spec themes that were
useful in a single spec but did not yet clear the direct-promotion bar.

`[SIGNAL]` — when all recommendations are straightforward promotions/refinements
with no contradictions, complex merges, or stale conflicts, auto-proceed to
Step 6. When a concern is flagged (contradictions, complex merges, or stale
conflicts requiring judgment), escalate one level per the `[SIGNAL]` escalation
rules and wait for the user to review before promoting, refining, merging, or
marking stale.

## Step 5c: Rebuild the ledger on explicit request

Only do this when the user explicitly asks for a ledger rebuild or confirms
that rebuild is the goal because the current ledger is noisy, missing, or
corrupted. Treat rebuild as a ledger-focused multi-spec sweep, not a third
permanent mode:

1. Scan all `done` specs and collect learnings from each `meta.yaml`.
2. Reapply the Step 5a direct-promotion bar and the Step 4b
   overlap/contradiction review to reconstruct candidate durable entries,
   grouped into `.spec/_ledger/{domain}.yaml` files using the existing schema
   and `source_spec` traceability.
3. Compare those candidate files against the current ledger, if it exists, to
   decide what to keep, what to refine, what to merge or mark stale, and where
   tags should be normalized.
4. Present the candidate domain files plus the major replacements/merges to the
   user for review. Human judgment stays in the loop; do not silently rewrite
   the ledger.
5. Only after explicit confirmation, replace the current curated ledger files
   with the reviewed candidate files. If the ledger is missing or sparse, write
   only the confirmed files you reconstructed.
6. Treat the reviewed rebuild result as the curated ledger that future
   `create-spec` research should consult first. Rebuild restores that surface;
   it does not bypass it.
7. Keep rebuild lightweight: no new schema, no script or background job, and no
   requirement to run it outside explicit cleanup/recovery requests.
