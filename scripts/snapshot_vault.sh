#!/usr/bin/env bash
set -euo pipefail

# Snapshot the current vault git repo into a dated folder and commit.
# Usage:
#   ./scripts/snapshot_vault.sh "Main Vault"
# If no name is provided, defaults to "Main Vault".
#
# Behavior:
# - Creates folder: YYYYMMDD-HHMM <Vault Name>
# - rsyncs the repo contents into that folder, excluding .git and previous snapshots
# - Shows status
# - Prompts for commit message (default: "<timestamp> <Vault Name> snapshot")
# - Commits and optionally pushes

vault_name="${1:-Main Vault}"
repo_root="$(pwd)"

if [ ! -d "$repo_root/.git" ]; then
  echo "Error: run this inside your vault git repo (where .git exists)." >&2
  exit 1
fi

timestamp="$(date +%Y%m%d-%H%M)"
snapshot_dir="${timestamp} ${vault_name}"

echo "Creating snapshot: ${snapshot_dir}"
mkdir -p "${snapshot_dir}"

# Exclude .git and previous timestamped snapshots to avoid nesting
rsync -a \
  --exclude '.git/' \
  --exclude '20??????-???? *' \
  ./ "${snapshot_dir}/"

echo "Snapshot contents staged in ${snapshot_dir}"

# Show status
git status --short

default_msg="${timestamp} ${vault_name} snapshot"
read -e -p "Commit message [${default_msg}]: " user_msg
commit_msg="${user_msg:-$default_msg}"

if [ -z "$commit_msg" ]; then
  echo "Aborting: empty commit message."
  exit 1
fi

git add "${snapshot_dir}"
git status --short

read -p "Proceed with commit? [Y/n]: " go
go=${go:-Y}
if [[ ! "$go" =~ ^[Yy]$ ]]; then
  echo "Aborted before commit."
  exit 0
fi

git commit -m "$commit_msg"
echo "Commit created."

read -p "Push to origin? [y/N]: " push_go
push_go=${push_go:-N}
if [[ "$push_go" =~ ^[Yy]$ ]]; then
  git push
  echo "Pushed to origin."
else
  echo "Not pushed. You can push later with: git push"
fi

