# Batch Scaffolding

Conditional workflow for create-spec when the user explicitly wants multiple
backlog items scaffolded in one session. Entered from Step 1 when the user
chooses batch scaffolding instead of a single bounded slice.

## Entering batch mode

When the user explicitly wants multiple backlog items scaffolded now:

1. Confirm which backlog items to scaffold and any sequencing notes
2. Create a `planning-{slug}` branch from `origin/HEAD` if not already on one
   (Step 4 of create-spec handles detection — if already on a `planning-*`
   branch, continue on it)
3. Continue through Steps 2–6 for each selected item
4. Use `depends_on` in downstream `meta.yaml` files where the backlog order
   implies sequencing
5. Keep every generated spec at `draft`
6. After all specs are scaffolded, push the `planning-*` branch and open a PR
   to merge the spec definitions to the default branch

## Batch mode effects on subsequent steps

- **Step 2 (Category):** Determine category for each selected backlog item
  before assigning IDs.
- **Step 3 (ID):** Assign sequential IDs and create one directory per selected
  backlog item.
- **Step 4 (Branch):** The first spec in the batch creates the `planning-*`
  branch. Subsequent specs in the same batch continue on it.
- **Step 6 (Sections):** Keep sections concise and draft-level. Do not begin
  research during the batch pass.
- **Step 7 (Blast radius):** Defer blast radius assessment to when each spec
  is individually researched. Classification requires populated scope and ACs,
  which are draft-level during batch scaffolding.
- **Step 8 (Research gate):** Stop before this step for every generated spec.
  Tell the user research is deferred and each scaffolded spec must come back
  through Steps 8 and 9 individually, typically in dependency order. No
  batch-created spec reaches `research` or `ready` during the batch scaffolding
  pass.
- **Step 9 (Mark ready):** Not part of the batch scaffolding pass. Each
  scaffolded draft reaches `ready` only when it is researched individually
  later.
