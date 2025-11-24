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
  printf "  RATECORE UPDATE - STEP %s/%s\n" "${num}" "${TOTAL_STEPS}"
  echo "========================================"
  log_info "${title}"
}

print_banner

step 1 "Checking tools"
require_command git
require_command go
require_command python3
ensure_dir "${ROOT_DIR}/.cache/go-build"
ensure_dir "${ROOT_DIR}/.gopath"
export GOCACHE="${ROOT_DIR}/.cache/go-build"
export GOPATH="${ROOT_DIR}/.gopath"
USE_POETRY=false
if [[ -f "${ROOT_DIR}/ratecore_bot/pyproject.toml" ]]; then
  USE_POETRY=true
  require_command poetry
else
  require_command pip
fi
log_success "Tooling available"

step 2 "Updating repository"
(cd "${ROOT_DIR}" && git pull)

step 3 "Tidying Go modules and rebuilding API"
(cd "${ROOT_DIR}" && go mod tidy)
if go build -o "${ROOT_DIR}/bin/ratecore-api" "${ROOT_DIR}/cmd/ratecore-api"; then
  log_success "Rebuilt Go API"
else
  log_error "Go build failed"
  exit 1
fi

step 4 "Updating Python dependencies"
if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  python3 -m venv "${ROOT_DIR}/.venv"
  log_info "Created .venv for dependency install"
fi
# shellcheck disable=SC1091
source "${ROOT_DIR}/.venv/bin/activate"

if [[ "${USE_POETRY}" == "true" ]]; then
  export POETRY_VIRTUALENVS_CREATE=false
  (cd "${ROOT_DIR}/ratecore_bot" && poetry update --without dev --no-interaction --no-root)
else
  if [[ -f "${ROOT_DIR}/requirements.txt" ]]; then
    pip install --upgrade -r "${ROOT_DIR}/requirements.txt"
  else
    log_warn "No requirements.txt found; skipping pip upgrade"
  fi
fi
log_success "Python dependencies updated"

step 5 "Update complete"
log_success "RateCore updated successfully."
echo "Run ./scripts/check.sh to verify status."
