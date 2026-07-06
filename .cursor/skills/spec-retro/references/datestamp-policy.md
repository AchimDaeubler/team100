# Datestamp Policy

Dates in `meta.yaml` (`created`, `updated`, completion dates, learning dates)
must come from the machine's local system clock — agents must never write a
date literal themselves.

## Rule

All `meta.yaml` date fields are set exclusively by scripts:

- **`status` and `updated`:** run the transition script
  (`.cursor/skills/create-spec/scripts/transition.ps1 <spec-directory> <status>`
  or `transition.sh <spec-directory> <status>`). The script calls
  `Get-Date -Format 'yyyy-MM-dd'` (PowerShell) or `date +%Y-%m-%d` (bash),
  both local time.
- **`created`:** set by the scaffold script at spec creation time.
- **Other dates** (completion, learnings): if no script covers the field,
  derive the value inline —
  `$(Get-Date -Format 'yyyy-MM-dd')` (PowerShell) or `$(date +%Y-%m-%d)`
  (bash) — never type a date string manually.

## Why

LLMs have no real-time clock. When asked to produce a date, they reason from
training priors (wrong year) or UTC (wrong day in western timezones after
evening). The only reliable mitigation is tool-mediated injection — the date
must come from a command, never from the model.
