#!/usr/bin/env bash

set -Eeuo pipefail

has_command() {
    command -v "$1" >/dev/null 2>&1
}

main() {
    printf '[INFO] Running read-only Terraform validation.\n'

    if ! has_command terraform; then
        printf '[FAIL] Terraform is not installed or is not on PATH. No installation was attempted.\n' >&2
        return 1
    fi

    local version
    version="$(terraform version 2>/dev/null | sed -n '1p')"
    printf '[OK] Terraform found: %s\n' "${version:-version output unavailable}"
}

main "$@"
