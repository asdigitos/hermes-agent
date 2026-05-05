#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Rollback the local Hermes runtime checkout to a previously known-good branch / commit.

Usage:
  rollback-local-hermes.sh [options]

Options:
  --repo PATH                     Hermes runtime repo (default: ~/.hermes/hermes-agent)
  --state-file PATH               State file with branch=... and sha=... entries
                                  (default: ~/.hermes/local-installation-last-known-good.env)
  --branch NAME                   Branch to restore
  --sha COMMIT                    Exact commit SHA to restore
  --allow-discard-local-changes   Allow hard reset even if working tree is dirty
  --no-gateway-refresh            Skip gateway stop/install/start
  -h, --help                      Show this help

Resolution order:
  1. explicit --branch / --sha
  2. values loaded from --state-file

Examples:
  scripts/rollback-local-hermes.sh
  scripts/rollback-local-hermes.sh --state-file ~/.hermes/local-installation-last-known-good.env
  scripts/rollback-local-hermes.sh --branch fix/mcp-add-command-routing --sha 9226ddb6193b4a2951f99652c1d8b4c5d02267ec
EOF
}

repo_path="$HOME/.hermes/hermes-agent"
state_file="$HOME/.hermes/local-installation-last-known-good.env"
target_branch=""
target_sha=""
allow_discard_local_changes=0
refresh_gateway=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      repo_path="$2"
      shift 2
      ;;
    --state-file)
      state_file="$2"
      shift 2
      ;;
    --branch)
      target_branch="$2"
      shift 2
      ;;
    --sha)
      target_sha="$2"
      shift 2
      ;;
    --allow-discard-local-changes)
      allow_discard_local_changes=1
      shift
      ;;
    --no-gateway-refresh)
      refresh_gateway=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

repo_path="${repo_path/#\~/$HOME}"
state_file="${state_file/#\~/$HOME}"

if [[ -z "$target_branch" || -z "$target_sha" ]]; then
  if [[ -f "$state_file" ]]; then
    # shellcheck disable=SC1090
    source "$state_file"
    target_branch="${target_branch:-${branch:-}}"
    target_sha="${target_sha:-${sha:-}}"
  fi
fi

if [[ ! -d "$repo_path/.git" && ! -f "$repo_path/.git" ]]; then
  echo "Repo path is not a git checkout: $repo_path" >&2
  exit 1
fi

if [[ -z "$target_branch" && -z "$target_sha" ]]; then
  echo "No rollback target resolved. Provide --branch / --sha or a valid --state-file." >&2
  exit 1
fi

cd "$repo_path"

current_branch=$(git branch --show-current || true)
current_sha=$(git rev-parse HEAD)
status_output=$(git status --porcelain)

if [[ -n "$status_output" && $allow_discard_local_changes -ne 1 ]]; then
  echo "Refusing rollback because working tree is dirty." >&2
  echo "Re-run with --allow-discard-local-changes if you intentionally want to discard local changes." >&2
  echo "$status_output" >&2
  exit 1
fi

mkdir -p "$HOME/.hermes/rollback-records"
rollback_record="$HOME/.hermes/rollback-records/$(date +%Y%m%dT%H%M%S)-before-rollback.env"
printf 'branch=%s\nsha=%s\ntime=%s\nrepo=%s\n' \
  "$current_branch" "$current_sha" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$repo_path" > "$rollback_record"

echo "[1/6] Fetching origin..."
git fetch origin --prune

echo "[2/6] Current runtime state"
echo "  branch: ${current_branch:-<detached>}"
echo "  sha:    $current_sha"
echo "  saved:  $rollback_record"
echo "  target branch: ${target_branch:-<detached>}"
echo "  target sha:    ${target_sha:-<branch-tip-only>}"

if [[ -n "$target_sha" ]]; then
  if ! git cat-file -e "$target_sha^{commit}" 2>/dev/null; then
    echo "Target commit is not present locally after fetch: $target_sha" >&2
    exit 1
  fi
fi

echo "[3/6] Restoring git checkout..."
if [[ -n "$target_branch" && -n "$target_sha" ]]; then
  git switch -C "$target_branch" "$target_sha"
elif [[ -n "$target_sha" ]]; then
  git switch --detach "$target_sha"
else
  git switch "$target_branch"
fi

if [[ -n "$target_sha" ]]; then
  git reset --hard "$target_sha"
fi

echo "[4/6] Post-checkout identity"
echo "  branch: $(git branch --show-current || true)"
echo "  sha:    $(git rev-parse HEAD)"

if [[ $refresh_gateway -eq 1 ]]; then
  if ! command -v hermes >/dev/null 2>&1; then
    echo "hermes command not found on PATH; cannot refresh gateway automatically." >&2
    exit 1
  fi

  echo "[5/6] Performing clean gateway refresh..."
  hermes gateway stop
  hermes gateway install --force
  hermes gateway start
else
  echo "[5/6] Skipping gateway refresh (--no-gateway-refresh)"
fi

echo "[6/6] Verification"
git status --short --branch
if [[ $refresh_gateway -eq 1 ]]; then
  hermes gateway status
fi

echo
echo "Rollback complete."
echo "Rollback record saved at: $rollback_record"
if [[ -f "$state_file" ]]; then
  echo "Input state file used: $state_file"
fi
