#!/usr/bin/env bash

set -Eeuo pipefail

has_command() {
    command -v "$1" >/dev/null 2>&1
}

service_property() {
    local property="$1"
    systemctl show jenkins --property="$property" --value 2>/dev/null || true
}

main() {
    printf '[INFO] Reporting Jenkins service state only. No logs, configuration, credentials, tokens, or passwords will be read.\n'

    if ! has_command systemctl; then
        printf '[FAIL] systemctl is unavailable; Jenkins service state cannot be checked.\n' >&2
        return 1
    fi

    local load_state active_state sub_state unit_file_state
    load_state="$(service_property LoadState)"
    active_state="$(service_property ActiveState)"
    sub_state="$(service_property SubState)"
    unit_file_state="$(service_property UnitFileState)"

    if [[ -z "$load_state" || "$load_state" == "not-found" ]]; then
        printf '[FAIL] Jenkins systemd service was not found. No installation was attempted.\n' >&2
        return 1
    fi

    printf 'LoadState: %s\n' "${load_state:-unknown}"
    printf 'ActiveState: %s\n' "${active_state:-unknown}"
    printf 'SubState: %s\n' "${sub_state:-unknown}"
    printf 'UnitFileState: %s\n' "${unit_file_state:-unknown}"

    if [[ "$active_state" != "active" ]]; then
        printf '[FAIL] Jenkins service is present but not active. No service action was attempted.\n' >&2
        return 1
    fi

    printf '[OK] Jenkins service is active.\n'
}

main "$@"
