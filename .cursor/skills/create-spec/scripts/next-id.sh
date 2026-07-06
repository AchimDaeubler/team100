#!/usr/bin/env bash
set -euo pipefail

# Allocates the next sequential spec ID (zero-padded to 3 digits).
# Uses GitHub ref claims for atomicity; falls back to local-only scan when
# gh CLI is unavailable or the remote is unreachable.

REPO_ROOT="$(git rev-parse --show-toplevel)"
SPEC_DIR="$REPO_ROOT/.spec"

get_local_max() {
  local max=0
  if [ ! -d "$SPEC_DIR" ]; then
    echo 0
    return
  fi
  for dir in "$SPEC_DIR"/SPEC-*/; do
    [ -d "$dir" ] || continue
    name="${dir%/}"
    name="${name##*/}"
    if [[ "$name" =~ ^SPEC-([0-9]+) ]]; then
      num=$((10#${BASH_REMATCH[1]}))
      if (( num > max )); then
        max=$num
      fi
    fi
  done
  echo "$max"
}

local_max=$(get_local_max)

if ! command -v gh >/dev/null 2>&1; then
  echo "warning: gh CLI not found — using local-only ID; number may collide with concurrent users" >&2
  printf "%03d\n" $((local_max + 1))
  exit 0
fi

# List existing remote claims
remote_max=0
refs_output=""
if refs_output=$(gh api "repos/{owner}/{repo}/git/matching-refs/spec-claims/SPEC-" --jq '.[].ref' 2>/dev/null); then
  if [ -n "$refs_output" ]; then
    while IFS= read -r ref; do
      if [[ "$ref" =~ SPEC-([0-9]+) ]]; then
        num=$((10#${BASH_REMATCH[1]}))
        if (( num > remote_max )); then
          remote_max=$num
        fi
      fi
    done <<< "$refs_output"
  fi
else
  echo "warning: could not list remote ref claims — using local-only ID; number may collide with concurrent users" >&2
  printf "%03d\n" $((local_max + 1))
  exit 0
fi

# Cross-check remote branches for spec IDs not covered by ref claims
branch_max=0
branch_output=""
if branch_output=$(gh api "repos/{owner}/{repo}/git/matching-refs/heads/SPEC-" --jq '.[].ref' 2>/dev/null); then
  if [ -n "$branch_output" ]; then
    while IFS= read -r ref; do
      if [[ "$ref" =~ SPEC-([0-9]+) ]]; then
        num=$((10#${BASH_REMATCH[1]}))
        if (( num > branch_max )); then
          branch_max=$num
        fi
      fi
    done <<< "$branch_output"
  fi
else
  echo "warning: could not list remote branches — branch collision check skipped" >&2
fi

# Cross-check open PR head branches for spec IDs
pr_max=0
pr_output=""
if pr_output=$(gh pr list --state open --json headRefName --jq '.[].headRefName' 2>/dev/null); then
  if [ -n "$pr_output" ]; then
    while IFS= read -r ref; do
      if [[ "$ref" =~ SPEC-([0-9]+) ]]; then
        num=$((10#${BASH_REMATCH[1]}))
        if (( num > pr_max )); then
          pr_max=$num
        fi
      fi
    done <<< "$pr_output"
  fi
else
  echo "warning: could not list open PRs — PR collision check skipped" >&2
fi

max=$(( local_max > remote_max ? local_max : remote_max ))
max=$(( max > branch_max ? max : branch_max ))
max=$(( max > pr_max ? max : pr_max ))
candidate=$(( max + 1 ))
sha="$(git rev-parse HEAD)"
max_retries=10

for (( i=0; i<max_retries; i++ )); do
  padded=$(printf "%03d" "$candidate")
  ref_name="refs/spec-claims/SPEC-$padded"

  result=""
  if result=$(gh api "repos/{owner}/{repo}/git/refs" -f "ref=$ref_name" -f "sha=$sha" 2>/dev/null); then
    printf "%03d\n" "$candidate"
    exit 0
  fi

  if echo "$result" | grep -q 'Reference already exists'; then
    candidate=$((candidate + 1))
    continue
  fi

  # Non-422 failure — fall back to local
  echo "warning: could not claim ref on remote — using local-only ID; number may collide with concurrent users" >&2
  printf "%03d\n" "$candidate"
  exit 0
done

echo "warning: exhausted retry attempts — using local-only ID; number may collide with concurrent users" >&2
printf "%03d\n" "$candidate"
exit 0
