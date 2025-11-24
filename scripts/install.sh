#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${SCRIPT_DIR}/helpers/colors.sh"
source "${SCRIPT_DIR}/helpers/banner.sh"
source "${SCRIPT_DIR}/helpers/system.sh"
source "${SCRIPT_DIR}/helpers/env.sh"

TOTAL_STEPS=8

step() {
  local num="$1"
  local title="$2"
  echo
  echo "========================================"
  printf "  RATECORE INSTALLER - STEP %s/%s\n" "${num}" "${TOTAL_STEPS}"
  echo "========================================"
  log_info "${title}"
}

print_banner

step 1 "Detecting operating system"
OS_NAME="$(detect_os)"
log_info "Detected OS: ${OS_NAME}"

step 2 "Checking prerequisites"
ensure_prereq() {
  local cmd="$1"
  local pkg="$2"
  if check_command "${cmd}"; then
    return 0
  fi
  if check_command apt-get; then
    read -r -p "Missing ${cmd}. Attempt to install ${pkg} via apt-get? [y/N]: " ans
    case "${ans}" in
      y|Y)
        log_info "Installing ${pkg} with apt-get (sudo may prompt)..."
        sudo apt-get update && sudo apt-get install -y "${pkg}"
        ;;
      *) log_error "Missing required command: ${cmd}"; exit 1 ;;
    esac
  else
    log_error "Missing required command: ${cmd} (install manually)"
    exit 1
  fi
}

install_poetry_with_pip() {
  local pip_cmd="pip3"
  if ! check_command "${pip_cmd}"; then
    if check_command pip; then
      pip_cmd="pip"
    else
      ensure_prereq pip3 python3-pip
    fi
  fi
  log_info "Installing poetry via ${pip_cmd} --user"
  ${pip_cmd} install --user -U poetry
  # shellcheck disable=SC2016
  local user_bin
  user_bin="$(python3 - <<'PY'
import sysconfig
print(sysconfig.get_path("scripts"))
PY
)"
  log_info "If poetry is not found, add ${user_bin} to PATH."
}

ensure_poetry() {
  if check_command poetry; then
    return 0
  fi

  if check_command apt-get; then
    read -r -p "Missing poetry. Attempt to install python3-poetry via apt-get? [y/N]: " ans
    case "${ans}" in
      y|Y)
        log_info "Installing python3-poetry with apt-get (sudo may prompt)..."
        if sudo apt-get update && sudo apt-get install -y python3-poetry; then
          return 0
        fi
        log_warn "Apt installation failed or package unavailable; falling back to pip."
        ;;
    esac
  fi

  install_poetry_with_pip

  if ! check_command poetry; then
    log_error "Poetry is still missing. Ensure ${HOME}/.local/bin (or your Python user scripts path) is in PATH."
    exit 1
  fi
}

ensure_prereq go golang-go
ensure_prereq python3 python3

PYTHON_BIN="${PYTHON_BIN:-python3}"

select_python() {
  if check_command python3.11; then
    PYTHON_BIN="python3.11"
    return
  fi

  local ver
  ver="$(${PYTHON_BIN} - <<'PY' 2>/dev/null || true
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
  local major="${ver%%.*}"
  local minor="${ver#*.}"
  if [[ -n "${minor}" ]]; then
    minor="${minor%%.*}"
  fi

  if [[ "${major}" == "3" && "${minor:-0}" -ge 13 ]]; then
    if check_command apt-get; then
      read -r -p "Detected Python ${ver}. Install python3.11 (+venv) via apt-get for compatibility? [y/N]: " ans
      case "${ans}" in
        y|Y)
          log_info "Installing python3.11 and python3.11-venv (sudo may prompt)..."
          sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv || true
          if check_command python3.11; then
            PYTHON_BIN="python3.11"
            return
          else
            log_warn "python3.11 not found after install attempt; continuing with ${PYTHON_BIN} (${ver})"
          fi
          ;;
        *)
          log_warn "Proceeding with ${PYTHON_BIN} ${ver}; pydantic-core may not support Python >=3.13."
          ;;
      esac
    else
      log_warn "Python ${ver} detected; install Python 3.11+venv for best compatibility."
    fi
  fi
}

select_python

PY_VER_NUM="$(${PYTHON_BIN} - <<'PY' 2>/dev/null || true
import sys
print(f\"{sys.version_info.major}.{sys.version_info.minor}\")
PY
)"
# Prefer Python <=3.12 for dependency compatibility; if running on >=3.13, attempt python3.12, otherwise exit.
if [[ "${PY_VER_NUM%%.*}" == "3" ]]; then
  minor="${PY_VER_NUM#*.}"
  minor="${minor%%.*}"
  if [[ "${minor:-0}" -ge 13 ]]; then
    if check_command python3.12; then
      PYTHON_BIN="python3.12"
      PY_VER_NUM="$(${PYTHON_BIN} - <<'PY' 2>/dev/null || true
import sys
print(f\"{sys.version_info.major}.{sys.version_info.minor}\")
PY
)"
      log_info "Switching to ${PYTHON_BIN} (${PY_VER_NUM}) for compatibility."
    else
      log_error "Python ${PY_VER_NUM} detected. Please install Python 3.12 (python3.12 and python3.12-venv) to continue."
      exit 1
    fi
  fi
fi

log_info "Using Python interpreter: ${PYTHON_BIN}"

USE_POETRY=false
if [[ -f "${ROOT_DIR}/ratecore_bot/pyproject.toml" ]]; then
  USE_POETRY=true
  ensure_poetry
else
  ensure_prereq pip python3-pip
fi
log_success "Prerequisites OK"

step 3 "Preparing directories"
ensure_dir "${ROOT_DIR}/logs"
ensure_dir "${ROOT_DIR}/data"
ensure_dir "${ROOT_DIR}/runtime"
ensure_dir "${ROOT_DIR}/bin"
ensure_dir "${ROOT_DIR}/.cache/go-build"
ensure_dir "${ROOT_DIR}/.gopath"
ensure_dir "${ROOT_DIR}/.cache/rustup"
ensure_dir "${ROOT_DIR}/.cache/cargo"
export GOCACHE="${ROOT_DIR}/.cache/go-build"
export GOPATH="${ROOT_DIR}/.gopath"
export RUSTUP_HOME="${ROOT_DIR}/.cache/rustup"
export CARGO_HOME="${ROOT_DIR}/.cache/cargo"
log_success "Directories ready"

step 4 "Configuring environment"
if [[ ! -f "${ROOT_DIR}/.env" ]]; then
  create_env_interactive
else
  log_info ".env already exists, skipping creation"
fi

step 5 "Building Go API"
if go build -o "${ROOT_DIR}/bin/ratecore-api" "${ROOT_DIR}/cmd/ratecore-api"; then
  log_success "Built Go API binary at bin/ratecore-api"
else
  log_error "Go build failed"
  exit 1
fi

step 6 "Setting up Python virtual environment"
if [[ -d "${ROOT_DIR}/.venv" ]]; then
  if [[ ! -w "${ROOT_DIR}/.venv" ]]; then
    log_warn ".venv exists but is not writable. Attempting to fix ownership..."
    if sudo chown -R "$(id -u)":"$(id -g)" "${ROOT_DIR}/.venv"; then
      log_success "Fixed .venv ownership."
    else
      log_error "Could not fix .venv ownership automatically. Remove it manually and rerun."
      exit 1
    fi
  fi
  current_py="$("${ROOT_DIR}/.venv/bin/python" - <<'PY' 2>/dev/null || true
import sys
print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"
  if [[ -n "${current_py}" ]]; then
    major="${current_py%%.*}"
    minor="${current_py#*.}"
    minor="${minor%%.*}"
    if [[ "${major}" == "3" && "${minor:-0}" -ge 13 ]]; then
      log_warn ".venv is using Python ${current_py}; recreating with ${PYTHON_BIN}"
      rm -rf "${ROOT_DIR}/.venv"
    fi
  fi
fi

if [[ ! -d "${ROOT_DIR}/.venv" ]]; then
  "${PYTHON_BIN}" -m venv "${ROOT_DIR}/.venv"
  log_success "Created virtual environment at .venv using ${PYTHON_BIN}"
else
  log_info "Reusing existing .venv"
fi

step 7 "Installing Python dependencies"
# shellcheck disable=SC1091
source "${ROOT_DIR}/.venv/bin/activate"

if [[ "${USE_POETRY}" == "true" ]]; then
  export PIP_PREFER_BINARY=1
  export POETRY_VIRTUALENVS_CREATE=false
  (cd "${ROOT_DIR}/ratecore_bot" && poetry install --without dev --no-interaction --no-root)
else
  if [[ -f "${ROOT_DIR}/requirements.txt" ]]; then
    pip install -r "${ROOT_DIR}/requirements.txt"
  else
    log_warn "No requirements.txt found; skipping Python dependency install"
  fi
fi
log_success "Python dependencies installed"

step 8 "Installation complete"
print_banner
log_success "RateCore is installed."
echo
echo "Next steps:"
echo "  - To adjust environment variables: ./scripts/setup.sh"
echo "  - To run the stack: ./scripts/run.sh"
echo "  - To check status: ./scripts/check.sh"
