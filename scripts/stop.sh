#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/helpers/colors.sh"
source "${SCRIPT_DIR}/helpers/banner.sh"

print_banner

echo
echo "========================================"
echo "  RATECORE STOPPER"
echo "========================================"

read -r -p "Stop Docker stack (if running)? [y/N]: " USE_DOCKER
if [[ "${USE_DOCKER}" =~ ^[Yy]$ ]]; then
  log_info "Stopping Docker services (sudo docker compose down)..."
  if sudo docker compose down; then
    log_success "Docker services stopped."
  else
    log_error "Failed to stop Docker services."
  fi
fi

# Stop local API if running
API_PID_FILE="${ROOT_DIR}/runtime/api.pid"
if [[ -f "${API_PID_FILE}" ]] && kill -0 "$(cat "${API_PID_FILE}")" >/dev/null 2>&1; then
  log_info "Stopping local Go API pid $(cat "${API_PID_FILE}")"
  kill "$(cat "${API_PID_FILE}")" 2>/dev/null || true
  rm -f "${API_PID_FILE}"
  log_success "Local Go API stopped."
fi

# Stop local bot if running in background (best-effort)
BOT_PIDS=$(pgrep -f "python -m ratecore_bot.main" || true)
if [[ -n "${BOT_PIDS}" ]]; then
  log_info "Stopping local bot process(es): ${BOT_PIDS}"
  kill ${BOT_PIDS} 2>/dev/null || true
  log_success "Local bot stopped (if it was running)."
else
  log_info "If the bot is running in this shell, press Ctrl+C to stop it."
fi
