# Research Gate

Core research procedure invoked from `.cursor/skills/create-spec/SKILL.md`.
This is the most important step — do not skip it.

1. Update `meta.yaml`: set `status: research`
2. Build a shared research brief for all four lanes:
   - spec `id`, `title`, and `category`
   - problem statement
   - any stack, domain, or subsystem context already visible in the repo
   - relevant keywords, likely files, or prior specs if already known
3. Read `research_subagents` from
   [`.spec/user-config.yaml`](user-profile.md) (absent or malformed → `true`)
   and pick the path. Either path covers the same four lanes against the same
   brief and produces the same attributed evidence shape; synthesis and
   downstream steps are identical.

   **Step 3A — Dispatch path** (`research_subagents: true`). Dispatch these
   four project subagents in parallel:
   - **`learnings-curator`** — search `.spec/_ledger/*.yaml` and `done` specs'
     `meta.yaml` learnings, then return ranked prior-learning candidates with
     relevance reasoning
   - **`repo-analyst`** — investigate current repo patterns, API assumptions,
     related specs, and likely affected files
   - **`docs-researcher`** — search current framework, library, and tool
     documentation relevant to the spec's stack and problem
   - **`prior-art-researcher`** — search industry patterns, known approaches,
     trade-offs, and common pitfalls for the problem class

   **Step 3B — Inline path** (`research_subagents: false`). The main agent
   performs all four investigations itself in a single evidence-gathering
   pass, grouping outputs by lane so curation and synthesis below work the
   same way as the dispatch path:
   - **Prior learnings (`learnings-curator` lane)** — search
     `.spec/_ledger/*.yaml` and `done` specs' `meta.yaml` learnings; rank
     candidates with relevance reasoning.
   - **Repo investigation (`repo-analyst` lane)** — survey current repo
     patterns, API assumptions, related specs, and likely affected files.
   - **Docs (`docs-researcher` lane)** — consult current framework, library,
     and tool documentation relevant to the spec's stack and problem.
   - **Prior art (`prior-art-researcher` lane)** — look up industry patterns,
     known approaches, trade-offs, and common pitfalls for the problem class.

   Produce lane-grouped findings in the same evidence shape the dispatched
   lanes would return. Do not skip any lane because it is "in head" — write
   each lane's evidence down so the synthesis below has something to
   cross-reference.

4. `[SIGNAL]` — review the lane results with mode-aware prior learnings
   curation before final synthesis:
   - Present the `learnings-curator` results grouped by source (`ledger` vs.
     `raw`), showing each learning's type, summary, source spec or file, and
     tags.
   - **Clean-signal criteria**: all returned learnings are relevant with no
     contradictions to other lane findings (or no notable prior learnings
     found). When clean, auto-include all returned learnings and proceed to
     synthesis.
   - **When a concern is flagged** (contradictions between learnings and other
     lane findings, clearly irrelevant results, or ambiguous relevance) —
     escalate one level per the `[SIGNAL]` escalation rules. Present the
     learnings for interactive curation: the user can dismiss irrelevant
     results or mark learnings to incorporate into the `Research` section.
   - If `.spec/_ledger/` doesn't exist or is empty, that lane should fall back
     to raw learnings without error.
   - If neither source produces useful prior learnings, note "No prior
     learnings found for this domain" and continue normally.
5. Treat the lane outputs as evidence, not authors. After the
   prior-learning curation checkpoint, the main agent must analytically
   synthesize the lane results regardless of which path produced them:
   - cross-reference internal and external findings
   - resolve contradictions explicitly
   - discard weak or noisy results
   - write the final `Research` and `Implementation guidance` sections in its
     own words rather than concatenating lane output
   - organize findings by conclusion, not by source lane — the final section
     should read as a unified analysis, not four mini-reports
6. Verify any claims you plan to carry forward before writing them into the
   spec:
   - confirm repo-local claims against repo-root-relative paths
   - prefer authoritative docs for documentation claims
   - keep prior-art findings clearly attributed as external precedent rather
     than repo fact
7. Populate the **Research** section with synthesized, conclusion-oriented
   findings. Each bullet must add distinct downstream signal — a decision,
   constraint, risk, open question, or implementation-shaping conclusion.
   Attribute each finding with compact inline provenance in parentheses,
   e.g. `(repo-analyst, docs-researcher)`, citing every lane that contributed.
   - Merge corroborating evidence from multiple lanes into one finding rather
     than repeating the same conclusion under different source headings.
   - Omit lanes that contributed no unique signal, or mention them briefly
     within a related finding — they do not need standalone bullets.
   - Do not create per-lane subsections or organize findings by source type.
     Structure by conclusion, not by origin.
   - Attribution reflects the lane that produced the evidence, not whether
     it ran as a subagent or inline on the main agent — downstream readers
     should not need to know the dispatch mode to understand the research.
   - If detailed supporting material is worth preserving beyond the synthesized
     bullets, place it in optional `.spec/.../resources/` notes rather than
     padding the main `Research` section.
8. Populate **Implementation guidance** with:
   - Files likely affected (specific repo-root-relative paths for repo files)
   - Files NOT to modify
   - Patterns to follow (reference specific existing code)
   - Test expectations
   - Local-only artifacts outside the repo described generically or anonymized
     rather than pasted as machine-specific paths
9. Salvage empty lane returns before declaring degradation (Step 3A only):
   - When a dispatched lane returns empty or whitespace-only output from
     `Await`, apply
     [subagent-dispatch.md](subagent-dispatch.md) to recover the lane's
     final message from its transcript before treating the lane as
     failed. A salvaged lane feeds synthesis with its attribution
     suffixed `(salvaged from transcript)` and does **not** trigger the
     fallback below or an unrequested inline rerun. Salvage is skipped
     entirely under Step 3B because the inline path does not dispatch
     subagents.
10. Graceful degradation (applies to both paths, independent of the toggle):
    - If a subagent is unavailable, a web tool fails, or an external lane
      returns no useful signal, do not block the research gate.
    - Briefly note the fallback and cover that lane inline if needed. A
      dispatch-path failure for one lane is distinct from the user choosing
      the inline path for all lanes — note the fallback in the lane's
      attribution so readers can see which lanes ran as subagents, which
      ran inline by preference, and which fell back to inline after a
      dispatch failure.
    - Repo-only findings are still sufficient when external research is
      unavailable or unproductive, as long as the limitation is stated plainly
      in the `Research` section.
