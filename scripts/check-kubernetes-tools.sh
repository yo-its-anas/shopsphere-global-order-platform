#!/usr/bin/env bash

set -Eeuo pipefail

failures=0

ok() {
    printf '[OK] %s\n' "$*"
}

fail() {
    printf '[FAIL] %s\n' "$*" >&2
    failures=$((failures + 1))
}

has_command() {
    command -v "$1" >/dev/null 2>&1
}

check_kubectl() {
    if ! has_command kubectl; then
        fail "kubectl is not installed or is not on PATH. No installation was attempted."
        return
    fi

    local version
    version="$(kubectl version --client=true 2>/dev/null | sed -n '1p')"
    ok "kubectl found: ${version:-version output unavailable}"
}

check_kind() {
    if ! has_command kind; then
        fail "kind is not installed or is not on PATH. No installation was attempted."
        return
    fi

    ok "kind found: $(kind version 2>/dev/null || printf 'version unavailable')"
}

main() {
    printf '[INFO] Checking Kubernetes client tools only; no cluster changes will be made.\n'
    check_kubectl
    check_kind

    if ((failures > 0)); then
        printf '[FAIL] Kubernetes tool validation found %d issue(s).\n' "$failures" >&2
        return 1
    fi

    printf '[OK] Kubernetes tool validation completed successfully.\n'
}

main "$@"
