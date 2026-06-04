#!/usr/bin/env bash
set -euo pipefail

# Create a downstream upstream-integration branch from origin/main and merge upstream/main.
# Intended for use in a non-runtime checkout or git worktree.

branch_name="${1:-integration/upstream-$(date +%Y%m%d)}"

repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"

current_branch=$(git branch --show-current)
if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to proceed: working tree is dirty on branch '$current_branch'." >&2
  exit 1
fi

echo "[1/5] Fetching remotes..."
git fetch origin --prune
git fetch upstream --prune

echo "[2/5] Refreshing local main from origin/main..."
git switch main
git pull --ff-only origin main

echo "[3/5] Creating integration branch: $branch_name"
git switch -c "$branch_name"

echo "[4/5] Merging upstream/main into $branch_name"
git merge --no-ff upstream/main

echo "[5/5] Done"
echo

echo "Next steps:"
echo "  - resolve any conflicts"
echo "  - review docs/downstream-deltas.md"
echo "  - run targeted regression tests"
echo "  - push with: git push -u origin $branch_name"
echo "  - open PR with gh pr create --base main --head $branch_name"
