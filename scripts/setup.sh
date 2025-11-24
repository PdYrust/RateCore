#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/helpers/colors.sh"
source "${SCRIPT_DIR}/helpers/banner.sh"
source "${SCRIPT_DIR}/helpers/system.sh"
source "${SCRIPT_DIR}/helpers/env.sh"

TOTAL_STEPS=2

step() {
  local num="$1"
  local title="$2"
  echo
  echo "========================================"
  printf "  RATECORE SETUP - STEP %s/%s\n" "${num}" "${TOTAL_STEPS}"
  echo "========================================"
  log_info "${title}"
}

mask_value() {
  local val="$1"
  if [[ -z "${val}" ]]; then
    echo "<empty>"
    return
  fi
  local len=${#val}
  if (( len <= 4 )); then
    echo "***"
  else
    echo "${val:0:2}***${val:len-2:2}"
  fi
}

print_banner

step 1 "Configure environment file"
read -r -p "Recreate .env now? [y/N]: " recreate
case "${recreate}" in
  y|Y) create_env_interactive ;;
  *) log_info "Skipping .env recreation";;
esac

step 2 "Environment summary"
if [[ -f "${ROOT_DIR}/.env" ]]; then
  load_env
  echo "Current values:"
  echo "  BOT_TOKEN: $(mask_value "${BOT_TOKEN:-}")"
  echo "  TELEGRAM_ADMIN_ID: ${TELEGRAM_ADMIN_ID:-<missing>}"
  echo "  RCORE_API_BASE_URL: ${RCORE_API_BASE_URL:-<missing>}"
  echo "  RCORE_HTTP_PORT: ${RCORE_HTTP_PORT:-8080}"
  echo "  RCORE_LOG_LEVEL: ${RCORE_LOG_LEVEL:-info}"
  echo "  RCORE_BINANCE_BASE_URL: ${RCORE_BINANCE_BASE_URL:-<default>}"
  echo "  RCORE_FOREX_BASE_URL: ${RCORE_FOREX_BASE_URL:-<default>}"
  echo "  RCORE_IRR_BASE_URL: ${RCORE_IRR_BASE_URL:-<default>}"
  echo "  RCORE_IRR_API_KEY: $(mask_value "${RCORE_IRR_API_KEY:-}")"
  echo "  RCORE_METALS_BASE_URL: ${RCORE_METALS_BASE_URL:-<default>}"
else
  log_warn "No .env found at ${ROOT_DIR}/.env. Run ./scripts/install.sh or ./scripts/setup.sh to create one."
fi

log_success "Setup complete."
