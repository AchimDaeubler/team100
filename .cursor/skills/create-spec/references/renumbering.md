# Renumbering a Spec

Renumber `SPEC-{old}` to `SPEC-{new}` after a collision has been detected.
Allocation-time prevention is elsewhere (SPEC-047 ref claims, SPEC-061
branch/PR cross-checks) — by the time you are reading this, the collision
has already slipped past those guards and the two IDs in conflict are known.

Renumbering is a guardrailed, single-shot operation. The script changes only
in-repo state (directory name + `id:` frontmatter); out-of-repo state
(branch names, PR titles, commit-message scopes) is a separate manual
checklist below. Do not re-run the script to "converge" after a partial
state — restore to a clean working tree and try again.

## When to renumber

Renumber when both of the following are true:

1. A spec has been assigned a number (directory `SPEC-{old}-{slug}/` exists,
   `spec.md` frontmatter says `id: SPEC-{old}`), **and**
2. A collision has been confirmed — another spec already uses `SPEC-{old}`
   and must keep it (it was published first, has an open PR, is already
   merged, or is otherwise authoritative). The loser is whichever spec is
   most movable, typically the local one that has not yet been pushed.

Do **not** renumber to close a sequential gap or to "tidy up" numbering.
Gaps are expected per `_shared/lifecycle.md` "Spec numbering".

## Preflight checklist

Confirm before running the script:

1. **The collision is real.** Both specs exist and both claim the same
   numeric ID. Use `ls .spec/ | grep SPEC-{old}` and, if a remote is in
   play, `gh pr list --search "SPEC-{old}"` to confirm.
2. **The new ID is free.** No local directory `.spec/SPEC-{new}-*/`
   exists; no remote branch `SPEC-{new}-*`; no open PR head named
   `SPEC-{new}-*`. The `create-spec/scripts/next-id.{sh,ps1}` allocator
   is the authoritative source for the next unused number when in doubt.
3. **The working tree is clean.** `git status --porcelain` is empty.
   Commit, stash, or discard pending changes first — the script refuses
   to run on a dirty tree so that `git mv` is unambiguous.
4. **You are on the correct branch.** Typically the `SPEC-{old}-{slug}`
   branch that scaffolded the losing spec. Renumbering is done on the
   feature branch so the rename lands in the same PR as the
   implementation.

## Run the script

Cross-platform script pair under `.cursor/skills/create-spec/scripts/`:

```bash
./renumber.sh <old-id> <new-id>
```

```powershell
.\renumber.ps1 <old-id> <new-id>
```

Both accept the bare or zero-padded form of each ID (`23` and `023` are
equivalent; output is always zero-padded). The script:

- validates that both IDs are 1–3 digits and not equal;
- refuses to run if the working tree is dirty;
- refuses to run if no `.spec/SPEC-{old}-*/` directory exists, if more
  than one matches, or if the old directory has no `spec.md`;
- refuses to run if `.spec/SPEC-{new}-*/` already exists locally;
- invokes `git mv` to rename the directory — with no `-f` flag, so
  git's own error on a pre-existing target is the authoritative gate;
- patches the first `id: SPEC-{old}` line inside the frontmatter block
  of the renamed `spec.md` in place, using a temp-file-and-`mv`
  pattern (bash) or an instance-method `[regex]::new($pattern).Replace($content, $replacement, 1)`
  bounded to the first match, paired with an explicit UTF-8-no-BOM
  write via `[System.IO.File]::WriteAllText` (PowerShell). The static
  `[regex]::Replace` has no `count` overload — its 4-arg form takes
  `RegexOptions`, not a replacement limit — so the instance form is the
  API shape to use when bounding to a single match.

Success emits a single summary line on stdout and nothing on stderr:

```
Renumbered SPEC-{old}-{slug} -> SPEC-{new}-{slug}
```

Failure exits non-zero with a message prefixed `error:` on stderr.

## Verify the result

After the script succeeds:

1. `git status --porcelain` shows per-file `R` lines for the rename plus
   a single `M` line for the renamed `spec.md`.
2. `head -3 .spec/SPEC-{new}-*/spec.md` shows `id: SPEC-{new}`.
3. `grep -F "SPEC-{old}" .spec/SPEC-{new}-*/spec.md` returns no matches
   — unless you intentionally kept historical prose like "was previously
   SPEC-{old}", which the script does not touch outside the `id:` line.
4. The dashboard (run `spec-dashboard`) shows the spec at the new ID and
   sorts it into the correct numeric position.

Commit the rename on the feature branch with a scoped `docs` commit:

```
docs(SPEC-{new}): renumber from SPEC-{old} to resolve collision
```

## Manual follow-up checklist

The script only changes the directory name and the frontmatter `id:`
line. Walk this checklist before pushing, and fix anything that still
points at the old ID:

1. **Other specs' `meta.yaml`.** Search for `depends_on` and `blocked_by`
   entries that reference the old ID. Each entry has the exact shape
   `  - "SPEC-{old}"` for `depends_on` or `    - spec: "SPEC-{old}"` for
   `blocked_by`:

   ```bash
   rg -n '"SPEC-{old}"' .spec/
   ```

   Update each occurrence to `"SPEC-{new}"` and commit with a scoped
   `docs` message.

2. **Prose references in other `spec.md` files.** Bare mentions like
   "see SPEC-{old}" or "depends on SPEC-{old}":

   ```bash
   rg -n "SPEC-{old}" .spec/ --glob '!SPEC-{new}-*/**'
   ```

   Update each or decide the historical reference is worth preserving
   (e.g., in a "previously known as" note).

3. **Ledger entries.** `.spec/_ledger/*.yaml` may include
   `source_spec:` or `corroborating_specs:` that name the old ID:

   ```bash
   rg -n "SPEC-{old}" .spec/_ledger/
   ```

   Update on purpose — ledger curation is otherwise `spec-retro`
   territory, so only fix genuine pointers, not historical attributions.

4. **Branch name.** `git branch -m SPEC-{old}-{slug} SPEC-{new}-{slug}`.
   If the branch has been pushed, also run
   `git push origin -u SPEC-{new}-{slug}` and delete the old remote
   branch (`git push origin --delete SPEC-{old}-{slug}`). The script
   does not touch branches — history rewrite territory varies by repo.

5. **Open PR title and body.** If a PR is already open on the old
   branch, `gh pr edit --title "SPEC-{new}: ..."` after the branch
   rename. GitHub re-associates the PR with the renamed branch
   automatically.

6. **Commit messages.** Commit messages on the feature branch still
   reference the old ID (`feat(SPEC-{old}): ...`). These are immutable
   without history rewrite; leaving them in place is normal — the PR
   title and squash-merge commit on the default branch will carry the
   new ID per `_shared/lifecycle.md` "Squash-merge commits".

7. **Refresh the dashboard.** Apply the `spec-dashboard` skill to
   regenerate `spec-dashboard.html` so the index reflects the new ID.

## What the script does NOT do

- **Detect collisions.** You tell the script which old ID to move to
  which new ID; it trusts the caller.
- **Allocate a new ID.** Run `create-spec/scripts/next-id.{sh,ps1}`
  first if you need one.
- **Rename branches, edit PR titles, or rewrite commit messages.**
  Those are out-of-repo state (or history-rewrite territory) and belong
  in the manual checklist above.
- **Fix cross-spec references in other files.** The preflight scopes
  rewrites to one directory; other specs' `meta.yaml`, ledger entries,
  and prose are the caller's responsibility.
- **Run twice to converge.** The preflight refuses partial states
  (existing `SPEC-{new}-*` directory, dirty tree). If a previous attempt
  left partial state, reset to a clean tree and run once.

## Preflight refusals — how to resolve

| Refusal | Resolution |
|---------|------------|
| `old-id must be 1-3 digits` / `new-id must be 1-3 digits` | Pass bare digits (`23` or `023`), not `SPEC-023` or paths. |
| `old-id and new-id are the same` | Nothing to renumber. |
| `working tree is dirty` | `git commit`, `git stash`, or `git restore` pending changes first. |
| `no directory found matching .spec/SPEC-{old}-*/` | The old ID is wrong, or the spec lives elsewhere. Check with `ls .spec/`. |
| `multiple directories match .spec/SPEC-{old}-*/` | Two or more directories claim the old ID locally. Resolve by hand — this is a local bookkeeping problem, not a renumbering problem. |
| `.spec/SPEC-{new}-* already exists` | The new ID is taken. Pick a different one with `next-id.{sh,ps1}`. |
| `git mv '...' failed: ...` | Unexpected — typically a filesystem permission issue or a race with another process. Re-run after resolving. |
