#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-platform"
readonly -a TOPICS=(
    "catalogue.product.created.v1"
    "catalogue.product.updated.v1"
    "catalogue.price.changed.v1"
    "inventory.adjusted.v1"
    "inventory.low.v1"
    "inventory.out-of-stock.v1"
    "inventory.reserved.v1"
    "inventory.reservation_released.v1"
    "inventory.reservation_consumed.v1"
)

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

main() {
    local pod_name=""
    local service_type=""
    local pvc_phase=""
    local descriptions=""
    local topic=""
    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status \
        statefulset/kafka --timeout=10s >/dev/null
    service_type="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get service kafka -o jsonpath='{.spec.type}')"
    [[ "$service_type" == "ClusterIP" ]] || fail "Kafka client Service is not ClusterIP-only."
    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod \
        -l app.kubernetes.io/name=kafka -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "Kafka pod was not found."
    pvc_phase="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pvc kafka-data-kafka-0 -o jsonpath='{.status.phase}')"
    [[ "$pvc_phase" == "Bound" ]] || fail "Kafka PVC is not Bound."
    descriptions="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- \
        /opt/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --describe)"
    for topic in "${TOPICS[@]}"; do
        grep -Eq "^Topic: ${topic}[[:space:]].*PartitionCount: 1[[:space:]].*ReplicationFactor: 1" \
            <<<"$descriptions" || fail "Topic is missing or violates the PoC partition/replication convention: ${topic}"
    done
    printf '[OK] Kafka is Ready, KRaft-only, persistent, ClusterIP-only, and all governed topics exist.\n'
}

main "$@"
