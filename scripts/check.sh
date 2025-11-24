#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/helpers/colors.sh"
source "${SCRIPT_DIR}/helpers/banner.sh"
source "${SCRIPT_DIR}/helpers/system.sh"
source "${SCRIPT_DIR}/helpers/env.sh"

TOTAL_STEPS=5

step() {
  local num="$1"
  local title="$2"
  echo
  echo "========================================"
  printf "  RATECORE STATUS CHECK - STEP %s/%s\n" "${num}" "${TOTAL_STEPS}"
  echo "========================================"
  log_info "${title}"
}

overall_status=0

ok() {
  log_success "✓ $1"
}

fail() {
  log_error "✗ $1"
  overall_status=1
}

warn() {
  log_warn "• $1"
}

print_banner

step 1 "Loading environment"
load_env

step 2 "Checking Go binary"
if [[ -x "${ROOT_DIR}/bin/ratecore-api" ]]; then
  ok "Go API binary present at bin/ratecore-api"
else
  fail "Go API binary missing (run ./scripts/install.sh)"
fi

step 3 "Checking API health"
PORT="${RCORE_HTTP_PORT:-8080}"
if check_command curl; then
  if curl -sf "http://localhost:${PORT}/api/v1/healthz" >/dev/null 2>&1; then
    ok "API health endpoint reachable on port ${PORT}"
  else
    warn "API not responding on http://localhost:${PORT}/api/v1/healthz"
  fi
else
  warn "curl not available; skipping HTTP health check"
fi

step 4 "Checking Python environment"
if [[ -d "${ROOT_DIR}/.venv" ]]; then
  ok ".venv present"
else
  fail ".venv missing (run ./scripts/install.sh)"
fi

# Check python import
if [[ -d "${ROOT_DIR}/.venv" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/.venv/bin/activate"
  export PYTHONPATH="${ROOT_DIR}/ratecore_bot:${PYTHONPATH:-}"
  if (cd "${ROOT_DIR}" && python - <<'PY' 2>/dev/null
from ratecore_bot import main  # noqa: F401
print("import-ok")
PY
  ); then
    ok "Python package importable (ratecore_bot)"
  else
    fail "Cannot import ratecore_bot (ensure dependencies are installed)"
  fi
fi

step 5 "Validating environment variables"
required_missing=0
for var in BOT_TOKEN TELEGRAM_ADMIN_ID RCORE_API_BASE_URL; do
  if [[ -z "${!var:-}" ]]; then
    fail "Environment variable ${var} is not set"
    required_missing=1
  fi
done
if [[ ${required_missing} -eq 0 ]]; then
  ok "Required environment variables are set"
fi

echo
if [[ ${overall_status} -eq 0 ]]; then
  log_success "All checks passed."
else
  log_warn "Some checks failed. See messages above."
fi

exit "${overall_status}"
