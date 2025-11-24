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
  printf "  RATECORE RUNNER - STEP %s/%s\n" "${num}" "${TOTAL_STEPS}"
  echo "========================================"
  log_info "${title}"
}

print_banner

# Optional: docker mode
read -r -p "Run with Docker compose? [y/N]: " USE_DOCKER
case "${USE_DOCKER}" in
  y|Y)
    log_info "Starting via docker compose up -d (sudo)..."
    if sudo docker compose up -d; then
      log_success "Docker services started. Tail logs with: docker compose logs -f"
      exit 0
    else
      log_error "docker compose up failed. Please fix and retry."
      exit 1
    fi
    ;;
  *)
    log_info "Proceeding with local run (API binary + bot)."
    ;;
esac

step 1 "Loading environment"
load_env
ensure_dir "${ROOT_DIR}/logs"
ensure_dir "${ROOT_DIR}/runtime"

ensure_writable() {
  local dir="$1"
  if [[ -w "${dir}" ]]; then
    return
  fi
  log_warn "${dir} is not writable. Attempting to fix ownership..."
  if sudo chown -R "$(id -u)":"$(id -g)" "${dir}"; then
    log_success "Fixed ownership for ${dir}"
  else
    log_error "Could not write to ${dir}. Please adjust permissions and rerun."
    exit 1
  fi
}

ensure_writable "${ROOT_DIR}/logs"
ensure_writable "${ROOT_DIR}/runtime"

API_BIN="${ROOT_DIR}/bin/ratecore-api"
API_PID_FILE="${ROOT_DIR}/runtime/api.pid"
DB_PATH="${ROOT_DIR}/ratecore_bot.db"

# Ensure SQLite DB is writable; fix ownership if needed.
if [[ -e "${DB_PATH}" && ! -w "${DB_PATH}" ]]; then
  log_warn "${DB_PATH} is not writable. Attempting to fix ownership..."
  if sudo chown "$(id -u)":"$(id -g)" "${DB_PATH}"; then
    log_success "Fixed ownership for ${DB_PATH}"
  else
    log_error "Could not write to ${DB_PATH}. Remove or fix permissions and rerun."
    exit 1
  fi
fi

step 2 "Starting Go API"
if [[ ! -x "${API_BIN}" ]]; then
  log_error "API binary not found at ${API_BIN}. Run ./scripts/install.sh first."
  exit 1
fi

if [[ -f "${API_PID_FILE}" ]] && kill -0 "$(cat "${API_PID_FILE}")" >/dev/null 2>&1; then
  log_warn "API already running with PID $(cat "${API_PID_FILE}")"
else
  if [[ -f "${API_PID_FILE}" ]]; then
    rm -f "${API_PID_FILE}"
  fi
  nohup "${API_BIN}" >> "${ROOT_DIR}/logs/api.log" 2>&1 &
  API_PID=$!
  echo "${API_PID}" > "${API_PID_FILE}"
  log_success "API started (pid ${API_PID}), logging to logs/api.log"
fi

step 3 "Starting Python bot"
if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  log_error ".venv not found. Run ./scripts/install.sh to create it."
  exit 1
fi

# shellcheck disable=SC1091
source "${ROOT_DIR}/.venv/bin/activate"

cd "${ROOT_DIR}"
export PYTHONPATH="${ROOT_DIR}/ratecore_bot:${PYTHONPATH:-}"
log_info "Running bot in foreground (Ctrl+C to stop)"
python -m ratecore_bot.main
