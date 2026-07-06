#!/usr/bin/env bash
set -euo pipefail

# Renumbers a spec after a collision is detected. Renames
# .spec/SPEC-{old}-{slug}/ to .spec/SPEC-{new}-{slug}/ via `git mv` and
# updates the `id:` frontmatter line in spec.md so the directory path and
# the frontmatter agree.
#
# Usage: renumber.sh <old-id> <new-id>
#   old-id — existing spec number (1-3 digits; "023" and "23" both accepted)
#   new-id — desired spec number (1-3 digits; "026" and "26" both accepted)
#
# Preflight refusals (non-zero exit, actionable error on stderr):
#   - args missing or not 1-3 digits
#   - old and new IDs are the same
#   - working tree is not clean (git status --porcelain non-empty)
#   - no directory .spec/SPEC-{old}-*/ exists, or more than one matches
#   - the old directory has no spec.md
#   - a directory .spec/SPEC-{new}-*/ already exists
#
# Does not renumber cross-spec references in other specs' meta.yaml or
# prose, rename branches, edit PR titles, or rewrite commit messages.
# See .cursor/skills/create-spec/references/renumbering.md for the
# manual follow-up checklist.

REPO_ROOT="$(git rev-parse --show-toplevel)"
SPEC_DIR="$REPO_ROOT/.spec"

if [ $# -lt 2 ]; then
  echo "error: usage: renumber.sh <old-id> <new-id>" >&2
  exit 1
fi

old_arg="$1"
new_arg="$2"

if ! [[ "$old_arg" =~ ^[0-9]{1,3}$ ]]; then
  echo "error: old-id '$old_arg' must be 1-3 digits" >&2
  exit 1
fi
if ! [[ "$new_arg" =~ ^[0-9]{1,3}$ ]]; then
  echo "error: new-id '$new_arg' must be 1-3 digits" >&2
  exit 1
fi

old_padded=$(printf "%03d" "$((10#$old_arg))")
new_padded=$(printf "%03d" "$((10#$new_arg))")

if [ "$old_padded" = "$new_padded" ]; then
  echo "error: old-id and new-id are the same (SPEC-$old_padded)" >&2
  exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
  echo "error: working tree is dirty. Commit or stash changes before renumbering." >&2
  exit 1
fi

shopt -s nullglob
old_candidates=("$SPEC_DIR"/SPEC-"$old_padded"-*/)
shopt -u nullglob

if [ ${#old_candidates[@]} -eq 0 ]; then
  echo "error: no directory found matching .spec/SPEC-$old_padded-*/" >&2
  exit 1
fi
if [ ${#old_candidates[@]} -gt 1 ]; then
  echo "error: multiple directories match .spec/SPEC-$old_padded-*/ - resolve manually" >&2
  exit 1
fi

old_dir="${old_candidates[0]%/}"
old_base="${old_dir##*/}"
slug="${old_base#SPEC-${old_padded}-}"
new_base="SPEC-${new_padded}-${slug}"
new_dir="$SPEC_DIR/$new_base"

old_spec="$old_dir/spec.md"
if [ ! -f "$old_spec" ]; then
  echo "error: spec.md not found at $old_spec" >&2
  exit 1
fi

shopt -s nullglob
new_existing=("$SPEC_DIR"/SPEC-"$new_padded"-*/)
shopt -u nullglob
if [ ${#new_existing[@]} -gt 0 ]; then
  echo "error: .spec/SPEC-$new_padded-* already exists - new ID is claimed locally" >&2
  exit 1
fi

mv_err=$(git mv "$old_dir" "$new_dir" 2>&1) || {
  echo "error: git mv '$old_base' -> '$new_base' failed: $mv_err" >&2
  exit 1
}

new_spec="$new_dir/spec.md"
sed -e '/^---$/,/^---$/ s|^id: SPEC-[0-9][0-9][0-9]$|id: SPEC-'"$new_padded"'|' \
    "$new_spec" > "$new_spec.tmp" && mv "$new_spec.tmp" "$new_spec"

echo "Renumbered $old_base -> $new_base"
