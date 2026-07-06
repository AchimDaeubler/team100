#!/usr/bin/env bash
set -euo pipefail

# Gathers repo context for debug-after-push: remote URL, current branch,
# HEAD SHA, service name, and deploy branch from the build workflow.

echo "=== Repo Context ==="

REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "unknown")
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
HEAD_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

echo "remote_url: $REMOTE_URL"
echo "branch: $BRANCH"
echo "head_sha: $HEAD_SHA"

WORKFLOW=".github/workflows/build.yml"

if [ -f "$WORKFLOW" ]; then
  SERVICE_NAME=$(grep -E '^\s+\w+:Dockerfile' "$WORKFLOW" 2>/dev/null | head -1 | sed 's/:.*//' | xargs || echo "")
  if [ -z "$SERVICE_NAME" ]; then
    SERVICE_NAME=$(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")")
    echo "service_name: $SERVICE_NAME (fallback: repo name)"
  else
    echo "service_name: $SERVICE_NAME"
  fi

  DEPLOY_BRANCH=$(grep -A1 'deploy' "$WORKFLOW" 2>/dev/null | grep -oP "refs/heads/\K[^'\"]*" | head -1 || echo "")
  if [ -z "$DEPLOY_BRANCH" ]; then
    DEPLOY_BRANCH=$(grep -oP "refs/heads/\K[^'\"]*" "$WORKFLOW" 2>/dev/null | head -1 || echo "unknown")
  fi
  echo "deploy_branch: $DEPLOY_BRANCH"
else
  echo "service_name: $(basename "$(git rev-parse --show-toplevel 2>/dev/null || echo "unknown")") (fallback: no workflow found)"
  echo "deploy_branch: unknown (no workflow found)"
fi
