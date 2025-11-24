#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/helpers/colors.sh"
source "${SCRIPT_DIR}/helpers/banner.sh"
source "${SCRIPT_DIR}/helpers/system.sh"
source "${SCRIPT_DIR}/helpers/env.sh"

TOTAL_STEPS=3

step() {
  local num="$1"
  local title="$2"
  echo
  echo "========================================"
  printf "  RATECORE UNINSTALL - STEP %s/%s\n" "${num}" "${TOTAL_STEPS}"
  echo "========================================"
  log_info "${title}"
}

print_banner

step 1 "Confirmation"
echo "This will remove built artifacts, virtualenv, runtime files, and optionally .env."
read -r -p "Proceed with uninstall? [y/N]: " confirm
case "${confirm}" in
  y|Y) ;;
  *) log_info "Uninstall aborted."; exit 0 ;;
esac

API_PID_FILE="${ROOT_DIR}/runtime/api.pid"

step 2 "Stopping services"
if [[ -f "${API_PID_FILE}" ]]; then
  API_PID="$(cat "${API_PID_FILE}")"
  if kill -0 "${API_PID}" >/dev/null 2>&1; then
    log_info "Stopping API (pid ${API_PID})"
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
  rm -f "${API_PID_FILE}"
else
  log_info "No API pidfile found; skipping stop."
fi

step 3 "Removing generated artifacts"
rm -f "${ROOT_DIR}/bin/ratecore-api"
rm -rf "${ROOT_DIR}/.venv"
rm -rf "${ROOT_DIR}/logs"
rm -rf "${ROOT_DIR}/runtime"
rm -rf "${ROOT_DIR}/data"
log_success "Removed binaries, virtualenv, logs, runtime, and data directories."

if [[ -f "${ROOT_DIR}/.env" ]]; then
  read -r -p "Delete .env as well? [y/N]: " delete_env
  case "${delete_env}" in
    y|Y)
      rm -f "${ROOT_DIR}/.env"
      log_info ".env removed."
      ;;
    *) log_info "Kept .env" ;;
  esac
fi

log_success "Uninstall complete. Source code and git history preserved."
