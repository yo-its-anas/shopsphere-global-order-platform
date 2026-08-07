#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_NAME="$(basename "$0")"
failures=0

info() {
    printf '[INFO] %s\n' "$*"
}

warn() {
    printf '[WARN] %s\n' "$*" >&2
    failures=$((failures + 1))
}

has_command() {
    command -v "$1" >/dev/null 2>&1
}

print_section() {
    printf '\n== %s ==\n' "$1"
}

report_os() {
    print_section "Operating system"
    if [[ -r /etc/os-release ]]; then
        # OS metadata is supplied by Ubuntu and contains no project secrets.
        # shellcheck disable=SC1091
        source /etc/os-release
        printf '%s\n' "${PRETTY_NAME:-${NAME:-Unknown Linux}}"
    else
        warn "Cannot read /etc/os-release."
        uname -srm
    fi
}

report_architecture() {
    print_section "Architecture"
    if has_command uname; then
        uname -m
    else
        warn "Required command 'uname' was not found."
    fi
}

report_cpu() {
    print_section "CPU"
    if has_command lscpu; then
        lscpu | awk -F: '/^(CPU\(s\)|Model name|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)):/ {gsub(/^[[:space:]]+/, "", $2); printf "%-24s %s\n", $1 ":", $2}'
    elif [[ -r /proc/cpuinfo ]]; then
        awk -F: '/^model name/ {gsub(/^[[:space:]]+/, "", $2); print $2; exit}' /proc/cpuinfo
        warn "'lscpu' was not found; CPU detail is limited."
    else
        warn "CPU information is unavailable."
    fi
}

report_memory() {
    print_section "Memory"
    if has_command free; then
        free -h
    else
        warn "Required command 'free' was not found."
    fi
}

report_disk() {
    print_section "Disk usage"
    if has_command df; then
        df -hP /
    else
        warn "Required command 'df' was not found."
    fi
}

report_timezone() {
    print_section "Timezone"
    if has_command timedatectl; then
        local timezone
        timezone="$(timedatectl show --property=Timezone --value 2>/dev/null || true)"
        if [[ -n "$timezone" ]]; then
            printf '%s\n' "$timezone"
            return
        fi
    fi

    if [[ -r /etc/timezone ]]; then
        sed -n '1p' /etc/timezone
    elif has_command date; then
        date '+%Z (%z)'
        warn "Canonical timezone name was unavailable; reported the current zone abbreviation and offset."
    else
        warn "Timezone information is unavailable."
    fi
}

report_listening_ports() {
    print_section "Listening TCP/UDP ports"
    if has_command ss; then
        # Deliberately omit process arguments and credentials.
        local socket_output
        socket_output="$(ss -lntu 2>&1 || true)"
        printf '%s\n' "$socket_output"
        if [[ "$socket_output" == *"Operation not permitted"* || "$socket_output" == *"Permission denied"* ]]; then
            warn "Socket details are restricted for the current execution context."
        fi
    elif has_command netstat; then
        netstat -lntu
        warn "'ss' was not found; used legacy 'netstat'."
    else
        warn "Neither 'ss' nor 'netstat' was found; listening ports cannot be reported."
    fi
}

main() {
    info "Running read-only host validation with ${SCRIPT_NAME}."
    report_os
    report_architecture
    report_cpu
    report_memory
    report_disk
    report_timezone
    report_listening_ports

    if ((failures > 0)); then
        printf '\n[WARN] Host validation completed with %d warning(s).\n' "$failures" >&2
        return 1
    fi

    printf '\n[OK] Host validation completed successfully.\n'
}

main "$@"
