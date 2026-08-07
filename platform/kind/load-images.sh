#!/usr/bin/env bash

set -Eeuo pipefail

readonly CLUSTER_NAME="shopsphere-poc"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

on_error() {
    local exit_code=$?
    local line_number="$1"
    printf '[ERROR] Image loading failed at line %s (exit %s).\n' "$line_number" "$exit_code" >&2
    exit "$exit_code"
}

trap 'on_error ${LINENO}' ERR

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found."
}

cluster_exists() {
    kind get clusters 2>/dev/null | grep -Fxq "$CLUSTER_NAME"
}

main() {
    require_command docker
    require_command kind

    (($# > 0)) || fail "Provide one or more existing local image references. Example: $0 shopsphere/customer-service:dev"
    docker info >/dev/null 2>&1 || fail "Docker daemon is not reachable by user '$(id -un)'."
    cluster_exists || fail "kind cluster '${CLUSTER_NAME}' does not exist. Run create-cluster.sh first."

    local image_reference
    for image_reference in "$@"; do
        docker image inspect "$image_reference" >/dev/null 2>&1 || fail "Local image '${image_reference}' does not exist; no image was pulled or built."
        printf '[INFO] Loading existing local image %q into cluster %q.\n' "$image_reference" "$CLUSTER_NAME"
        kind load docker-image --name "$CLUSTER_NAME" "$image_reference"
    done

    printf '[OK] Requested local images are available to the kind node.\n'
}

main "$@"
