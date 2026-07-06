#!/usr/bin/env bash
set -euo pipefail

# Compares ready_sha against HEAD for files listed in the spec's
# "Files likely affected" section. Prints changed files, if any.
#
# Usage: freshness-diff.sh <spec-directory> [--name-status]
#   --name-status  optional; shows rename/delete status instead of names only

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ $# -lt 1 ]; then
  echo "error: usage: freshness-diff.sh <spec-directory> [--name-status]" >&2
  exit 1
fi

spec_dir="$1"
diff_flag="--name-only"
if [ "${2:-}" = "--name-status" ]; then
  diff_flag="--name-status"
fi

if [[ "$spec_dir" != /* ]] && [[ ! "$spec_dir" =~ ^[A-Za-z]: ]]; then
  spec_dir="$REPO_ROOT/$spec_dir"
fi

meta_file="$spec_dir/meta.yaml"
spec_file="$spec_dir/spec.md"

if [ ! -f "$meta_file" ]; then
  echo "error: meta.yaml not found at $meta_file" >&2
  exit 1
fi

if [ ! -f "$spec_file" ]; then
  echo "error: spec.md not found at $spec_file" >&2
  exit 1
fi

ready_sha=""
while IFS= read -r line; do
  if [[ "$line" =~ ^ready_sha:[[:space:]]*(.*) ]]; then
    ready_sha="${BASH_REMATCH[1]}"
    ready_sha="${ready_sha//\"/}"
    ready_sha="${ready_sha# }"
    break
  fi
done < "$meta_file"

if [ -z "$ready_sha" ]; then
  echo "info: no ready_sha in meta.yaml, skipping freshness check" >&2
  exit 0
fi

if ! git rev-parse --verify "${ready_sha}^{commit}" >/dev/null 2>&1; then
  echo "warning: ready_sha $ready_sha is not a valid commit in this repo" >&2
  echo "recommendation: full re-research" >&2
  exit 0
fi

extract_paths() {
  local in_section=0
  while IFS= read -r line; do
    if [[ "$line" =~ [Ff]iles[[:space:]]likely[[:space:]]affected ]]; then
      in_section=1
      continue
    fi
    if [ "$in_section" -eq 1 ]; then
      if [[ "$line" =~ [Ff]iles[[:space:]]NOT[[:space:]]to[[:space:]]modify ]] \
         || [[ "$line" =~ ^## ]] \
         || [[ "$line" =~ [Pp]atterns[[:space:]]to[[:space:]]follow ]] \
         || [[ "$line" =~ [Tt]est[[:space:]]expectations ]]; then
        break
      fi
      local path=""
      if [[ "$line" =~ \`([^\`]+)\` ]]; then
        path="${BASH_REMATCH[1]}"
      elif [[ "$line" =~ ^[[:space:]]*[-\*][[:space:]]+([^[:space:]]+\.[^[:space:]]+) ]]; then
        path="${BASH_REMATCH[1]}"
      fi
      if [ -n "$path" ]; then
        echo "$path"
      fi
    fi
  done < "$spec_file"
}

paths=()
while IFS= read -r p; do
  [ -n "$p" ] && paths+=("$p")
done < <(extract_paths)

if [ ${#paths[@]} -eq 0 ]; then
  echo "info: no file paths extracted from spec.md, skipping path-limited diff" >&2
  exit 0
fi

git diff "$diff_flag" "$ready_sha" HEAD -- "${paths[@]}" || test $? = 1
