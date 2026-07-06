# Conflict Resolution During Completion

Automatic rebase and conflict handling for the completion workflow
(Step 8, sub-step 6). The agent performs this before pushing.

## Prerequisites

- Working tree is clean (`git status --porcelain` returns empty)
- Current branch matches `SPEC-*` pattern — if not, skip this procedure
  entirely with a warning
- Target branch is resolved: read `branching.target_branch` from `meta.yaml`;
  if absent, use the repo's default branch

## Safe rebase sequence

### 1. Fetch

```
git fetch origin <target_branch>
```

If fetch fails (offline, auth error), emit a `[NOTE]` warning and skip the
rest of this procedure — proceed to the push sub-step, which will surface its
own error.

### 2. Check divergence

```
git rev-list --count HEAD..origin/<target_branch>
```

If the count is `0`, the branch is up to date. Skip rebase and proceed to push.

### 3. Dry-run conflict detection (Git 2.38+)

```
git merge-tree --write-tree HEAD origin/<target_branch>
```

Exit code `0` = clean merge possible. Proceed to step 4.
Exit code `1` = conflicts exist. Classify severity (see tiers below) before
deciding whether to proceed.

### 4. Create backup branch

```
git branch SPEC-<n>-backup
```

This is the rollback point if anything goes wrong.

### 5. Attempt rebase

```
git rebase origin/<target_branch>
```

**If rebase succeeds (exit code 0):**

Git auto-resolved all hunks. This covers the **trivial** tier — non-overlapping
changes in the same or different files. Emit a tier-appropriate message (see
below) and proceed to push with `--force-with-lease`.

**If rebase fails (exit code 1 / stops at a conflict):**

Enumerate conflicts:

```
git ls-files --unmerged
git status --porcelain
```

Classify each conflicted file (see tiers below). Then either resolve or abort.

### 6. Post-resolution verification

After resolving any conflict (simple tier), before continuing the rebase:

1. Run a syntax/parse check on each resolved file if the project has a linter
   or type checker available
2. If the project has a test suite, run it after the full rebase completes
3. If any verification fails, treat the conflict as non-trivial — abort and
   escalate

### 7. Push after rebase

After a successful rebase (with or without resolution), push with:

```
git push --force-with-lease -u origin HEAD
```

Never use `--force`. `--force-with-lease` prevents overwriting remote changes
that arrived after the fetch.

### 8. Cleanup

Delete the backup branch after a successful push:

```
git branch -D SPEC-<n>-backup
```

If the rebase was aborted, restore from backup:

```
git rebase --abort
git reset --hard SPEC-<n>-backup
git branch -D SPEC-<n>-backup
```

## Conflict tiers

### Trivial — git auto-resolves

Non-overlapping changes across different files or non-overlapping hunks within
the same file. The `ort` merge strategy (Git 2.33+) handles these without
manual intervention.

**Detection:** Rebase succeeds (exit code 0) despite the branch being behind.

**Resolution:** Automatic — no agent action needed beyond the rebase itself.

**Messaging:**

| Mode | Behavior |
|------|----------|
| guided | `[NOTE]` — "Rebased your branch onto the latest target. Git resolved all changes automatically — no overlaps found." |
| safe-auto | `[NOTE]` — "Rebased onto latest target. No conflicts." |
| expert | Silent |
| streamlined | Silent |

### Simple — agent can resolve

Overlapping changes where the intent is clear and the resolution is mechanical.
Indicators:

- Lock files (`package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`) — regenerate
  rather than merge
- Adjacent or overlapping dependency entries in `package.json`, `Cargo.toml`,
  `requirements.txt`, or similar manifest files — union both additions
- Import blocks where both sides added different imports — include all
- Non-overlapping additions inside the same function or block that happen to
  touch adjacent lines

**Detection:** After a failed rebase, `git ls-files --unmerged` lists files.
Inspect each conflicted region. If all regions in all files match the patterns
above, classify as simple.

**Resolution:**

- Lock files: accept theirs (`git checkout --theirs <file>`) then regenerate
  using the project's package manager
- Manifest/import conflicts: edit to include both sides' additions, remove
  conflict markers, `git add <file>`, `git rebase --continue`
- Remember: during rebase, "ours" = target branch, "theirs" = feature branch
  (inverted from merge semantics)

**Messaging:**

| Mode | Behavior |
|------|----------|
| guided | `[CHECK]` — block. List each resolved file and what was done. Ask for confirmation before continuing. |
| safe-auto | `[CHECK]` — block. Summarize resolutions. Ask for confirmation. |
| expert | `[CHECK]` — inform. "Auto-resolved overlapping changes in `<files>`: `<summary>`." |
| streamlined | `[CHECK]` — inform. "I reconciled your work with recent changes — here's what I adjusted: `<summary>`." |

### Non-trivial — agent must not resolve

Conflicts where autonomous resolution risks introducing bugs. Indicators:

- Logic changes in the same function or method
- Structural changes (renamed/moved files where both sides diverged)
- Architectural disagreements (different approaches to the same problem)
- Any conflict the agent is uncertain about
- Post-resolution verification failure (syntax check or test failure)

**Detection:** After a failed rebase, any conflicted region that does not match
the simple-tier patterns above is non-trivial.

**Resolution:** Do not attempt. Abort the rebase and restore the branch.

```
git rebase --abort
git reset --hard SPEC-<n>-backup
git branch -D SPEC-<n>-backup
```

**Messaging:**

| Mode | Behavior |
|------|----------|
| guided | `[STOP]` — "The rebase produced conflicts I can't safely resolve. Here are the conflicting files and regions: `<details>`. Options: (1) resolve together in co-coding, (2) pause and get help, (3) I can show the full diff." |
| safe-auto | `[STOP]` — "Non-trivial conflicts in `<files>`. Rebase aborted, branch restored. Manual resolution needed." |
| expert | `[STOP]` — "Non-trivial conflict in `<files>`: `<conflict summary>`. Branch restored to pre-rebase state." |
| streamlined | `[STOP]` — "Your work overlaps with recent changes in a way I can't safely reconcile on my own. Let's pause and sort this out together — I'll show you what's overlapping." |

## Rebase semantics reminder

During `git rebase`, the directional terms are inverted from `git merge`:

| Term | During rebase means | During merge means |
|------|--------------------|--------------------|
| ours | Target branch (the branch being rebased onto) | Current branch |
| theirs | Feature branch (the commits being replayed) | Branch being merged in |

All `--ours` / `--theirs` flags and user-facing descriptions must account for
this inversion.

## When to skip

Skip the entire procedure (no fetch, no rebase) when:

- Not on a `SPEC-*` branch — warn and proceed to push
- Working tree is dirty — warn and proceed to push (the completion workflow
  should have committed everything, so this indicates a problem)
- `git fetch` fails — `[NOTE]` and proceed to push

The agent never auto-rebases on `main`, the default branch, or any branch
whose name does not match the `SPEC-*` pattern.
