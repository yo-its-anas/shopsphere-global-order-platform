#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
readonly CLUSTER_NAME="shopsphere-poc"
readonly KUBE_CONTEXT="kind-${CLUSTER_NAME}"
readonly CONFIG_FILE="${SCRIPT_DIR}/cluster-config.yaml"
readonly POC_OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc"

info() {
    printf '[INFO] %s\n' "$*"
}

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

on_error() {
    local exit_code=$?
    local line_number="$1"
    printf '[ERROR] Cluster setup failed at line %s (exit %s). No automatic deletion or replacement was attempted.\n' "$line_number" "$exit_code" >&2
    exit "$exit_code"
}

trap 'on_error ${LINENO}' ERR

require_command() {
    local command_name="$1"
    command -v "$command_name" >/dev/null 2>&1 || fail "Required command '${command_name}' was not found. Install it explicitly before retrying."
}

cluster_exists() {
    kind get clusters 2>/dev/null | grep -Fxq "$CLUSTER_NAME"
}

verify_prerequisites() {
    require_command docker
    require_command kind
    require_command kubectl

    docker info >/dev/null 2>&1 || fail "Docker daemon is not reachable by user '$(id -un)'. No privilege or service change was attempted."
    [[ -r "$CONFIG_FILE" ]] || fail "kind configuration not found: ${CONFIG_FILE}"
    [[ -r "${POC_OVERLAY}/kustomization.yaml" ]] || fail "PoC Kubernetes overlay not found: ${POC_OVERLAY}"
}

create_or_reuse_cluster() {
    if cluster_exists; then
        info "Cluster '${CLUSTER_NAME}' already exists; reusing it idempotently."
        info "This script never replaces an existing cluster. Use delete-cluster.sh, with explicit confirmation, if recreation is genuinely intended."
        return
    fi

    info "Creating single-control-plane kind cluster '${CLUSTER_NAME}'."
    kind create cluster \
        --name "$CLUSTER_NAME" \
        --config "$CONFIG_FILE" \
        --wait 120s
}

wait_for_node() {
    info "Waiting for the single cluster node to report Ready."
    kubectl --context "$KUBE_CONTEXT" wait \
        --for=condition=Ready \
        node \
        --all \
        --timeout=180s
}

apply_foundation() {
    info "Applying namespaces, ResourceQuotas, and LimitRanges from the PoC overlay."
    kubectl --context "$KUBE_CONTEXT" apply -k "$POC_OVERLAY"
}

print_status() {
    printf '\n== Cluster nodes ==\n'
    kubectl --context "$KUBE_CONTEXT" get nodes -o wide

    printf '\n== ShopSphere namespaces ==\n'
    kubectl --context "$KUBE_CONTEXT" get namespaces \
        -l app.kubernetes.io/part-of=shopsphere

    printf '\n== Baseline quotas ==\n'
    kubectl --context "$KUBE_CONTEXT" get resourcequota --all-namespaces

    printf '\n== Baseline limit ranges ==\n'
    kubectl --context "$KUBE_CONTEXT" get limitrange --all-namespaces

    printf '\n[OK] Cluster foundation is ready. This single-node cluster is not highly available.\n'
}

main() {
    verify_prerequisites
    create_or_reuse_cluster
    wait_for_node
    apply_foundation
    print_status
}

main "$@"
