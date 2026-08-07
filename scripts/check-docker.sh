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

check_docker_cli() {
    if ! has_command docker; then
        fail "Docker CLI is not installed or is not on PATH. No installation was attempted."
        return 1
    fi

    ok "Docker CLI found: $(docker --version 2>/dev/null || printf 'version unavailable')"
}

check_daemon_and_access() {
    if docker info >/dev/null 2>&1; then
        ok "Docker daemon is reachable by user '$(id -un)'."
        return
    fi

    if has_command systemctl && systemctl is-active --quiet docker 2>/dev/null; then
        fail "Docker service is active, but user '$(id -un)' cannot query it. Check authorized Docker group or socket access; do not use credentials in scripts."
    else
        fail "Docker daemon is not reachable. It may be stopped, absent, or inaccessible to user '$(id -un)'."
    fi
}

check_compose() {
    if docker compose version >/dev/null 2>&1; then
        ok "Docker Compose available: $(docker compose version --short 2>/dev/null || docker compose version 2>/dev/null)"
    else
        fail "Docker Compose plugin is unavailable. No installation was attempted."
    fi
}

check_buildx() {
    if docker buildx version >/dev/null 2>&1; then
        ok "Docker Buildx available: $(docker buildx version 2>/dev/null)"
    else
        fail "Docker Buildx plugin is unavailable. No installation was attempted."
    fi
}

main() {
    printf '[INFO] Running read-only Docker validation.\n'
    if check_docker_cli; then
        check_daemon_and_access
        check_compose
        check_buildx
    fi

    if ((failures > 0)); then
        printf '[FAIL] Docker validation found %d issue(s).\n' "$failures" >&2
        return 1
    fi

    printf '[OK] Docker validation completed successfully.\n'
}

main "$@"
