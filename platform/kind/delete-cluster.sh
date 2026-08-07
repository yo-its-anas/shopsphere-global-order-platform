#!/usr/bin/env bash

set -Eeuo pipefail

readonly CLUSTER_NAME="shopsphere-poc"
readonly CONFIRMATION="delete ${CLUSTER_NAME}"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

on_error() {
    local exit_code=$?
    local line_number="$1"
    printf '[ERROR] Cluster deletion failed at line %s (exit %s).\n' "$line_number" "$exit_code" >&2
    exit "$exit_code"
}

trap 'on_error ${LINENO}' ERR

cluster_exists() {
    kind get clusters 2>/dev/null | grep -Fxq "$CLUSTER_NAME"
}

confirm_deletion() {
    [[ -t 0 ]] || fail "Interactive confirmation is required; refusing to delete from a non-interactive session."

    printf 'This will delete kind cluster %q and all workloads stored inside it.\n' "$CLUSTER_NAME"
    printf 'Type %q to continue: ' "$CONFIRMATION"

    local response
    IFS= read -r response
    [[ "$response" == "$CONFIRMATION" ]] || fail "Confirmation did not match; cluster was not deleted."
}

main() {
    command -v kind >/dev/null 2>&1 || fail "Required command 'kind' was not found."

    if ! cluster_exists; then
        printf '[OK] Cluster %q does not exist; nothing to delete.\n' "$CLUSTER_NAME"
        return
    fi

    confirm_deletion
    kind delete cluster --name "$CLUSTER_NAME"
    printf '[OK] Cluster %q was deleted after explicit confirmation.\n' "$CLUSTER_NAME"
}

main "$@"
