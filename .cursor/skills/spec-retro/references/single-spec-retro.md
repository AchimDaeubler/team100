# Single-Spec Retro (Steps 3a–5a)

Evaluate and curate learnings from a just-completed spec. This is the default
next action after `agent-coding` completes a spec.

**Branch context:** Stay on the implementation branch — do not switch to the
default branch. All retro commits land on the same branch as the implementation
and appear on the spec's PR. If running a deferred retro and the implementation
branch no longer exists (PR already merged), create a `retro-SPEC-{n}` branch
from `origin/HEAD` for promotion commits and open a PR after curation
completes. See spec-retro Step 2 for full branch-context rules.

## Step 3a: Evaluate each learning

For every learning in the spec's `meta.yaml`, assess three quality dimensions:

| Dimension | Good | Needs improvement |
|-----------|------|-------------------|
| **Clarity** | Summary is a complete sentence; context explains why it matters | Vague or jargon-heavy; reader can't act on it without the spec open |
| **Specificity** | Names concrete files, patterns, APIs, or constraints | Generic observation that could apply to any codebase |
| **Reusability** | Useful to someone working in this domain who hasn't read this spec | Only meaningful in the context of this specific implementation |

These dimensions determine whether a learning is strong enough to keep or
improve. They do not by themselves justify ledger promotion; Step 5a applies a
higher durability bar.

When the ledger exists, compare each learning against matching ledger entries
too. A reusable learning may still be better handled as a refinement to an
existing entry than as a new promotion.

## Step 4a: Improve low-quality learnings and record the PR URL

`[SIGNAL]` — meta.yaml improvements confirmation.

For learnings that need improvement, propose edits:

1. Rewrite vague summaries to be self-contained
2. Add missing context (file paths, pattern names, error messages)
3. Normalize tags to lowercase-hyphenated (consistent with existing convention)

Also write the spec's PR URL to `meta.yaml.completion.pull_requests` here.
Retro is the single point in the Creator lifecycle that populates this field —
the completion workflow no longer does so. Invoke the idempotent
`.cursor/skills/agent-coding/scripts/capture-pr.sh <spec-directory> <pr-url>`
(bash/zsh) or `.ps1` (PowerShell) script; re-invoking with a URL already
recorded is a no-op.

Source the URL by retro-entry path:

- **Auto-chained from completion in the same session:** use the URL already in
  session context from `gh pr create`.
- **Standalone on the implementation `SPEC-{n}-*` branch (still exists) or on
  `retro-SPEC-{n}` (PR already merged, implementation branch deleted):** if
  `completion.pull_requests` is empty, recover the URL via

  ```
  gh pr list --head <branch> --state all --json url --limit 1
  ```

  (`--state all` returns merged PRs too). Fall back to prompting the user when
  `gh` is unavailable or returns nothing.

Bundle the PR URL write into the Step 4a `meta.yaml` commit when that commit
already carries learning improvements. When Step 4a produces no other meta
edits, commit the PR URL as a dedicated `chore(SPEC-{n}): record PR URL`
commit so the "separate commits per concern" convention still holds.

Present improvements to the user for confirmation. Update the spec's `meta.yaml`
with accepted improvements — commit separately from later curation actions per
[Git operations](lifecycle.md#git-operations).

## Step 5a: Choose the ledger outcome

For each strong learning, choose one of three outcomes:

| Outcome | Use when |
|---------|----------|
| **Promote as a new ledger entry** | The learning is already strong on clarity, specificity, and reusability; it is likely to matter across multiple future specs or captures a durable repo seam/contract/testing strategy; and the ledger does not already capture it |
| **Refine an existing ledger entry** | The ledger already captures the durable idea, but this spec gives you better wording, clearer context, tag normalization, duplicate/merge evidence, or evidence that an existing entry is stale or contradicted |
| **Keep in spec-local history** | The learning is useful but still narrow, implementation-local, one-off, or not yet corroborated enough for the curated ledger |

Do not promote directly to the ledger just because a learning seems reusable.
Keep it in the source spec's `meta.yaml` or reflect it in human-facing docs
when it is useful but still narrow, one-off, or local, such as:

- Bootstrap or setup details tied to this spec's implementation path
- Runtime or debugging observations, incident notes, or temporary workarounds
- File-local implementation details that future specs can rediscover from the
  source spec when needed

If a learning looks promising but is not yet clearly durable, defer it to
multi-spec sweep. Repeated patterns and corroborated cross-spec themes should
usually be elevated there rather than from a single spec in isolation.

For each learning, recommend one of the three outcomes. Step 6 auto-applies
straightforward recommendations per the `[SIGNAL]` mode behavior — see
[curation-workflow.md](curation-workflow.md) for clean-signal criteria and
escalation rules.
