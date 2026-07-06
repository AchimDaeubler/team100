#!/usr/bin/env bash
set -euo pipefail

# Updates status and updated fields in a spec's meta.yaml.
# Optionally captures ready_sha when transitioning to ready.
#
# Usage: transition.sh <spec-directory> <target-status>
#   spec-directory — path to the spec directory (e.g. .spec/SPEC-042-my-feature/)
#   target-status  — draft | research | ready | in_progress | blocked | done | cancelled | superseded

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ $# -lt 2 ]; then
  echo "error: usage: transition.sh <spec-directory> <target-status>" >&2
  exit 1
fi

spec_dir="$1"
target_status="$2"

# Resolve relative paths against repo root
if [[ "$spec_dir" != /* ]] && [[ ! "$spec_dir" =~ ^[A-Za-z]: ]]; then
  spec_dir="$REPO_ROOT/$spec_dir"
fi

meta_file="$spec_dir/meta.yaml"

if [ ! -f "$meta_file" ]; then
  echo "error: meta.yaml not found at $meta_file" >&2
  exit 1
fi

valid_statuses="draft research ready in_progress blocked done cancelled superseded"
if ! echo "$valid_statuses" | grep -qw "$target_status"; then
  echo "error: invalid status '$target_status'. Must be one of: $valid_statuses" >&2
  exit 1
fi

today="$(date +%Y-%m-%d)"

sed -i.bak "s|^status:.*|status: ${target_status}|" "$meta_file" && rm "$meta_file.bak"
sed -i.bak "s|^updated:.*|updated: ${today}|" "$meta_file" && rm "$meta_file.bak"

if [ "$target_status" = "ready" ]; then
  current_sha="$(git rev-parse HEAD)"
  if grep -q '^ready_sha:' "$meta_file"; then
    sed -i.bak "s|^ready_sha:.*|ready_sha: \"${current_sha}\"|" "$meta_file" && rm "$meta_file.bak"
  else
    echo "ready_sha: \"${current_sha}\"" >> "$meta_file"
  fi
fi

if [ "$target_status" = "done" ]; then
  if ! grep -q '^completion:' "$meta_file"; then
    {
      echo ""
      echo "completion:"
      echo "  date: ${today}"
      echo "  pull_requests: []"
    } >> "$meta_file"
  fi
fi

echo "Transitioned $(basename "$spec_dir") to $target_status"
