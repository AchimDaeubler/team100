#!/usr/bin/env bash
set -euo pipefail

# Records ready_sha in a spec's meta.yaml from current git rev-parse HEAD.
# Only used during the ready transition — ready_sha is immutable after that.
#
# Usage: capture-sha.sh <spec-directory>

REPO_ROOT="$(git rev-parse --show-toplevel)"

if [ $# -lt 1 ]; then
  echo "error: usage: capture-sha.sh <spec-directory>" >&2
  exit 1
fi

spec_dir="$1"

if [[ "$spec_dir" != /* ]] && [[ ! "$spec_dir" =~ ^[A-Za-z]: ]]; then
  spec_dir="$REPO_ROOT/$spec_dir"
fi

meta_file="$spec_dir/meta.yaml"

if [ ! -f "$meta_file" ]; then
  echo "error: meta.yaml not found at $meta_file" >&2
  exit 1
fi

current_sha="$(git rev-parse HEAD)"

if grep -q '^ready_sha:' "$meta_file"; then
  sed -i.bak "s|^ready_sha:.*|ready_sha: \"${current_sha}\"|" "$meta_file" && rm "$meta_file.bak"
else
  echo "ready_sha: \"${current_sha}\"" >> "$meta_file"
fi

echo "$current_sha"
