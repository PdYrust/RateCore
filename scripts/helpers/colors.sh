#!/usr/bin/env bash

# Simple color helpers for consistent logging across scripts.
RESET="\033[0m"
BOLD="\033[1m"
BLUE="\033[34m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"

log_info() {
  printf "${BLUE}[INFO]${RESET} %s\n" "$*"
}

log_warn() {
  printf "${YELLOW}[WARN]${RESET} %s\n" "$*"
}

log_error() {
  printf "${RED}[ERROR]${RESET} %s\n" "$*"
}

log_success() {
  printf "${GREEN}[OK]${RESET} %s\n" "$*"
}
