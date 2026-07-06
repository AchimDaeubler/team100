#!/usr/bin/env bash
set -euo pipefail

# Creates a spec directory with spec.md and meta.yaml from templates.
#
# Usage: scaffold.sh <id> <slug> <category> <owner> [depends_on...]
#   id       — zero-padded spec number (e.g. "042")
#   slug     — kebab-case short name (e.g. "my-feature")
#   category — feature | bug | refactoring | testing
#   owner    — git config user.name (human-readable display name)
#   depends_on — optional SPEC IDs for depends_on entries (e.g. "SPEC-040" "SPEC-041")

REPO_ROOT="$(git rev-parse --show-toplevel)"
SPEC_DIR="$REPO_ROOT/.spec"
TEMPLATES_DIR="$REPO_ROOT/.cursor/skills/create-spec/assets/templates"

if [ $# -lt 4 ]; then
  echo "error: usage: scaffold.sh <id> <slug> <category> <owner> [depends_on...]" >&2
  exit 1
fi

spec_id="$1"
slug="$2"
category="$3"
owner="$4"
shift 4
depends_on=("$@")

if [ -z "$owner" ]; then
  echo "error: owner parameter is empty. Pass the output of 'git config user.name'." >&2
  exit 1
fi

git_name="$(git config user.name 2>/dev/null || true)"
if [ -z "$git_name" ]; then
  echo "warning: git config user.name is not configured. The owner value '$owner' will be used as-is." >&2
fi

valid_categories="feature bug refactoring testing"
if ! echo "$valid_categories" | grep -qw "$category"; then
  echo "error: invalid category '$category'. Must be one of: $valid_categories" >&2
  exit 1
fi

template_file="$TEMPLATES_DIR/${category}-spec.md"
if [ ! -f "$template_file" ]; then
  echo "error: template not found at $template_file" >&2
  exit 1
fi

meta_template="$TEMPLATES_DIR/meta.yaml"
if [ ! -f "$meta_template" ]; then
  echo "error: meta.yaml template not found at $meta_template" >&2
  exit 1
fi

dir_name="SPEC-${spec_id}-${slug}"
spec_path="$SPEC_DIR/$dir_name"

if [ -d "$spec_path" ]; then
  echo "error: directory already exists: $spec_path" >&2
  exit 1
fi

mkdir -p "$spec_path"

today="$(date +%Y-%m-%d)"

sed \
  -e "s|{n}|${spec_id}|g" \
  -e "s|{title}|${slug}|g" \
  -e "s|{owner}|${owner}|g" \
  -e "s|category: feature|category: ${category}|g" \
  "$template_file" > "$spec_path/spec.md"

sed \
  -e "s|{date}|${today}|g" \
  "$meta_template" > "$spec_path/meta.yaml"

if [ ${#depends_on[@]} -gt 0 ]; then
  {
    echo ""
    echo "depends_on:"
    for dep in "${depends_on[@]}"; do
      echo "  - \"$dep\""
    done
  } >> "$spec_path/meta.yaml"
fi

echo "$spec_path"
