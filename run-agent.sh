#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [[ -d ".venv" ]]; then
  source ".venv/bin/activate"
fi

# Default log file unless user already provided --log-md
DEFAULT_LOG="./answer.md"
USE_LOG=true
for arg in "$@"; do
  if [[ "$arg" == --log-md* ]]; then
    USE_LOG=false
    break
  fi
done

if $USE_LOG; then
  python3 main.py chat --log-md "$DEFAULT_LOG" "$@"
else
  python3 main.py chat "$@"
fi

