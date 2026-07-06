<!-- Shared reference: canonical source is `.cursor/skills/_shared/subagent-dispatch.md`. Edit there, then run `./sync.sh`; do not hand-edit copied `references/` files. -->

# Subagent Dispatch — Transcript Salvage

Recovery procedure for parallel-lane subagent dispatch
(`Task` + `run_in_background: true` + `Await`). When the runtime
intermittently returns empty output for a lane whose subagent actually
completed, salvage the lane's final message from its transcript file
before declaring the lane failed.

Applies to research lanes (`create-spec` research gate, `agent-coding`
freshness targeted re-research, `brainstorming` approach viability) and
review lanes (`pr-review` Step 3A). Salvage is additive — it runs only
when Await returns empty, never rewrites a clean return, and hands
recovered output to the call site's existing synthesis step.

## 1. When to attempt salvage

Attempt salvage for a lane if and only if **both** hold:

- The lane ran under `run_in_background: true` and was polled with `Await`.
- The parent received no usable text from the lane — Await reports
  `output_length: 0`, or the returned text is empty or whitespace-only.

Do not attempt salvage when:

- The lane returned any non-empty non-whitespace text (even if short).
  A non-empty return is the authoritative result; salvage never
  overrides it.
- The lane failed to launch (no dispatch response, no transcript path).
  That is a true dispatch failure — skip salvage and run the call site's
  existing fallback directly.

Salvage is idempotent: re-invoking it for the same empty lane in the
same dispatch must not cause duplicate attributions or re-dispatch.

## 2. How to obtain the transcript path

Capture the transcript path from the **runtime**, per lane, at dispatch
time. Two equivalent sources:

- The `Task` dispatch response includes a line of the form
  `monitor its output by tailing the transcript at: <absolute-path>`.
- The `Await` tool response exposes the same path as
  `output_file_path`.

Retain the path per-lane alongside the lane's attribution.

Never reconstruct the path from a template such as
`agent-transcripts/<parent-id>/subagents/<subagent-id>.jsonl`. The
actual location is workspace-hashed under `~/.cursor/projects/<hash>/`
and is neither documented nor stable; the runtime is the only source of
truth. Cursor's public docs name a different surface
(`~/.cursor/subagents/`) that does not match the observed layout.

Normalize backslashes to forward slashes before passing the path to
`Read`. On Linux/WSL the runtime currently emits Windows-style
separators (`\home\user\.cursor\projects\…`) that `Read` cannot open
as-is. Replacement is mechanical: `path.replace('\\', '/')`.

Never print the transcript path to the user — the runtime's guardrail
("do not mention the transcript path to the user") applies to salvage
narration too.

## 3. JSONL parse recipe

Transcript files are line-delimited JSON (`.jsonl`). Read the whole
file, then parse each line independently:

1. Split on newlines. Discard empty lines.
2. For each line, attempt `JSON.parse`. Wrap in try/except — **skip
   lines that fail to parse**. A failing line is a partial or in-flight
   write, not a fatal error. Do not abort the scan.
3. Collect successfully-parsed records in order.

Do not assume the schema is stable across Cursor versions. Guard every
field access with a type check; treat missing or mis-typed fields as
"this record does not qualify" and keep scanning.

## 4. Substance heuristic — pick the salvage target

Scan the parsed records **from last to first**. The salvage target is
the last record where all of these hold:

- `record.role == "assistant"`.
- `record.message` is an object and `record.message.content` is a list.
- The content list contains at least one block with `block.type ==
  "text"` and a string `block.text`.
- Summing `block.text` across **only** `type == "text"` blocks and
  stripping whitespace yields **≥ 200 characters**.

Tool-use narration blocks (`block.type == "tool_use"`,
`"thinking"`, etc.) do **not** count toward the threshold — they
represent mid-flight reasoning, not the lane's final message. Earlier
assistant messages (interim tool-use turns) are skipped by the
last-to-first scan.

The recovered payload is the concatenation of the qualifying record's
`type == "text"` block texts (joined in order, single blank line
between blocks). This is the lane's salvaged output.

## 5. Hand off to synthesis

The salvaged payload is handed to the call site's existing synthesis
step **as if the lane had returned cleanly**. Downstream verdict,
anti-gaming, and research-synthesis logic are unchanged — salvage
changes only where the evidence came from, never what the evidence
means.

Suffix the lane's attribution with ` (salvaged from transcript)` so
synthesis and audit output distinguish recovered lanes from clean
returns. For example, a `pr-review` verdict note reads
`Dimension 3 — scope-drift-reviewer (salvaged from transcript)`; a
`create-spec` research bullet reads
`(repo-analyst (salvaged from transcript), docs-researcher)`.

Salvaged lanes count toward the call site's success threshold — a
lane recovered from transcript is a **successful lane**, not a lane
failure. In `pr-review`, a salvaged lane does not count against the
"≥ 2 lane failures → full inline Step 3B" rule. In research-gate
dispatches, a salvaged lane populates its evidence without triggering
a re-dispatch or an unrequested inline rerun.

## 6. Narration

Emit exactly one `[NOTE]` line per salvaged lane. The line names the
lane and states that its output was recovered from the transcript; it
must **not** include the transcript path.

Example:

> `[NOTE]` Lane `repo-analyst` returned empty; recovered its output
> from the transcript.

`[NOTE]` visibility follows the mode grid in
[agent-tags.md](agent-tags.md): blocks in `guided`, informs in
`safe-auto`, silent in `expert`, fully invisible in `streamlined`.

Do not upgrade to `[SIGNAL]` or `[CHECK]` — salvage is informational,
not a user checkpoint.

## 7. True-failure handoff

Declare the lane failed, run the call site's existing fallback
(inline dimension / Step 3B / inline lane coverage / advisory), and
emit a `[NOTE]` noting that salvage was attempted and failed, when
**any** of these hold:

- The transcript path was not captured from the dispatch response
  (runtime silently dropped it).
- The transcript file does not exist, cannot be read, or is empty.
- No record in the transcript satisfies the substance heuristic in §4
  (no qualifying `assistant` record, all candidate records below the
  200-character threshold, or all content blocks are tool-use /
  thinking only).

Do **not** re-dispatch the subagent. Do **not** invent content from
partial blocks that fell under the substance threshold — truncated
output is less reliable than the call site's fallback.

Example failure narration:

> `[NOTE]` Lane `prior-art-researcher` returned empty and salvage
> from the transcript did not find a qualifying final message; falling
> back to inline coverage for this lane.

## 8. Scope guardrails

- Salvage reads one file per empty lane via `Read`. No subprocess, no
  new dependency, no write to the transcript, no change to the
  `Task` / `Await` tool contract.
- Salvage is per-dispatch and per-lane: it does not cache, persist, or
  retroactively recover lanes from earlier sessions.
- Salvage is read-only: it never edits the transcript, never
  re-interprets the subagent's output, and never reformats recovered
  text beyond the `(salvaged from transcript)` attribution suffix.
- Subagent frontmatter uses `is_background: true` (the agent file's
  default dispatch mode); `Task` callers pass `run_in_background: true`
  per invocation. Salvage applies whenever a lane is polled with
  `Await`, regardless of which flag path put it in the background.
