#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGETS=(
  ".venv"
  "venv"
  "ratecore_bot/.venv"
  "ratecore_bot/venv"
  "__pycache__"
  "**/__pycache__"
  ".mypy_cache"
  ".pytest_cache"
  "build"
  "dist"
  ".idea"
  ".vscode"
  "logs"
  "log"
  "runtime"
  "tmp"
  "cache"
  ".cache"
)

FILES=(
  ".env"
  "ratecore_bot/.env"
  "env"
  "*.db"
  "*.sqlite"
  "*.sqlite3"
  "*.log"
  "nohup.out"
  "ratecore_bot.db"
)

deleted=()
missing=()

echo "Cleaning workspace at ${ROOT_DIR}"

remove_path() {
  local path="$1"
  if compgen -G "${ROOT_DIR}/${path}" > /dev/null; then
    sudo rm -rf "${ROOT_DIR}/${path}" && deleted+=("${path}") || true
  else
    missing+=("${path}")
  fi
}

for t in "${TARGETS[@]}"; do
  remove_path "$t"
done

for f in "${FILES[@]}"; do
  remove_path "$f"
done

echo
echo "Deleted:"
for d in "${deleted[@]}"; do
  echo "  - ${d}"
done

echo
echo "Skipped (not found):"
for m in "${missing[@]}"; do
  echo "  - ${m}"
done
