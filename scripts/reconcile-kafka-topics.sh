#!/usr/bin/env bash

set -Eeuo pipefail

readonly KUBE_CONTEXT="${KUBE_CONTEXT:-kind-shopsphere-poc}"
readonly NAMESPACE="shopsphere-platform"
readonly BROKER="127.0.0.1:9092"
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
    "order.created.v1"
    "order.confirmed.v1"
    "order.status_changed.v1"
    "order.cancelled.v1"
)

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

main() {
    local pod_name=""
    local topic=""
    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    pod_name="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get pod \
        -l app.kubernetes.io/name=kafka -o jsonpath='{.items[0].metadata.name}')"
    [[ -n "$pod_name" ]] || fail "Kafka pod was not found."
    kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" wait \
        --for=condition=Ready "pod/${pod_name}" --timeout=10s >/dev/null
    for topic in "${TOPICS[@]}"; do
        kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- \
            /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BROKER" \
            --create --if-not-exists --topic "$topic" --partitions 1 \
            --replication-factor 1 >/dev/null
        kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" exec "$pod_name" -- \
            /opt/kafka/bin/kafka-configs.sh --bootstrap-server "$BROKER" \
            --entity-type topics --entity-name "$topic" --alter \
            --add-config retention.ms=604800000,cleanup.policy=delete >/dev/null
        printf '[OK] Topic reconciled: %s\n' "$topic"
    done
}

main "$@"
