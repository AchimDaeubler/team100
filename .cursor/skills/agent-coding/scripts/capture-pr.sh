#!/usr/bin/env bash
set -euo pipefail

# Appends a PR URL to meta.yaml's completion.pull_requests list.
# Invoked by spec-retro (auto-chained or standalone). Idempotent:
# re-invoking with a URL already present in pull_requests is a no-op.
# The completion block with pull_requests: [] must already exist.
#
# Usage: capture-pr.sh <spec-directory> <pr-url>

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ $# -lt 2 ]; then
  echo "error: usage: capture-pr.sh <spec-directory> <pr-url>" >&2
  exit 1
fi

spec_dir="$1"
pr_url="$2"

if [[ "$spec_dir" != /* ]] && [[ ! "$spec_dir" =~ ^[A-Za-z]: ]]; then
  spec_dir="$REPO_ROOT/$spec_dir"
fi

meta_file="$spec_dir/meta.yaml"

if [ ! -f "$meta_file" ]; then
  echo "error: meta.yaml not found at $meta_file" >&2
  exit 1
fi

if ! grep -q '^completion:' "$meta_file"; then
  echo "error: no completion block found in $meta_file. Run transition.sh to done first." >&2
  exit 1
fi

lines=()
while IFS= read -r line || [ -n "$line" ]; do
  lines+=("$line")
done < "$meta_file"

# Idempotency pre-check: walk real (non-commented) list entries under the
# pull_requests: key and exact-match against $pr_url. The template keeps
# a commented `# pull_requests:` example that must not be treated as real.
pr_found=false
in_pull_requests=false
for line in "${lines[@]}"; do
  if [[ "${line}" =~ ^[[:space:]]*# ]]; then
    continue
  fi
  if [[ "$line" =~ pull_requests: ]]; then
    if [[ "$line" =~ \[\] ]]; then
      in_pull_requests=false
    else
      in_pull_requests=true
    fi
    continue
  fi
  if $in_pull_requests; then
    if [[ "${line}" =~ ^[[:space:]]*-[[:space:]] ]]; then
      entry="${line#"${line%%[^[:space:]]*}"}"
      entry="${entry#- }"
      entry="${entry#\"}"
      entry="${entry%\"}"
      if [[ "$entry" == "$pr_url" ]]; then
        pr_found=true
        break
      fi
    else
      in_pull_requests=false
    fi
  fi
done

if $pr_found; then
  echo "PR URL already recorded in $(basename "$spec_dir")/meta.yaml"
  exit 0
fi

output=()
i=0
while [ $i -lt ${#lines[@]} ]; do
  line="${lines[$i]}"

  # Skip YAML comment lines — the template block contains a commented
  # pull_requests: that must not be treated as a real field.
  is_comment=false
  if [[ "${line}" =~ ^[[:space:]]*# ]]; then
    is_comment=true
  fi

  if [[ "$is_comment" == false ]] && [[ "$line" =~ pull_requests:.*\[\] ]]; then
    indent="${line%%[^[:space:]]*}"
    output+=("${indent}pull_requests:")
    output+=("${indent}  - \"${pr_url}\"")
    i=$((i+1))
    continue
  fi

  if [[ "$is_comment" == false ]] && [[ "$line" =~ pull_requests: ]] && [[ ! "$line" =~ \[\] ]]; then
    output+=("$line")
    i=$((i+1))
    while [ $i -lt ${#lines[@]} ] && [[ "${lines[$i]}" =~ ^[[:space:]]*-[[:space:]] ]]; do
      output+=("${lines[$i]}")
      i=$((i+1))
    done
    indent="${line%%[^[:space:]]*}"
    output+=("${indent}  - \"${pr_url}\"")
    continue
  fi

  output+=("$line")
  i=$((i+1))
done

printf '%s\n' "${output[@]}" > "$meta_file"

echo "Added $pr_url to $(basename "$spec_dir")/meta.yaml"
