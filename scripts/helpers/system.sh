#!/usr/bin/env bash

detect_os() {
  case "$(uname -s)" in
    Linux*) echo "linux" ;;
    Darwin*) echo "darwin" ;;
    *) echo "unknown" ;;
  esac
}

check_command() {
  command -v "$1" >/dev/null 2>&1
}

require_command() {
  if ! check_command "$1"; then
    if declare -f log_error >/dev/null 2>&1; then
      log_error "Missing required command: $1"
    else
      echo "Missing required command: $1" >&2
    fi
    exit 1
  fi
}

ensure_dir() {
  local dir="$1"
  if [[ -z "$dir" ]]; then
    return
  fi
  if [[ ! -d "$dir" ]]; then
    mkdir -p "$dir"
  fi
}
