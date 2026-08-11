#!/usr/bin/env bash

set -Eeuo pipefail

readonly SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
readonly REPOSITORY_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
readonly OVERLAY="${REPOSITORY_ROOT}/platform/kubernetes/overlays/poc/kafka"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

require_text() {
    local content="$1"
    local expected="$2"
    grep -Fq -- "$expected" <<<"$content" || fail "Required Kafka configuration was not found: ${expected}"
}

main() {
    local rendered=""
    command -v kubectl >/dev/null 2>&1 || fail "Required command 'kubectl' was not found."
    rendered="$(kubectl kustomize "$OVERLAY")"
    [[ -n "$rendered" ]] || fail "Kafka overlay rendered no resources."
    grep -Eqi 'zookeeper' <<<"$rendered" && fail "ZooKeeper configuration is not allowed in this KRaft deployment."
    grep -Eq '^[[:space:]]+type: (NodePort|LoadBalancer)$' <<<"$rendered" && fail "Kafka must not be externally exposed."
    require_text "$rendered" "image: apache/kafka:4.3.1"
    require_text "$rendered" "value: broker,controller"
    require_text "$rendered" "value: INTERNAL://kafka-0.kafka-headless.shopsphere-platform.svc.cluster.local:9092"
    require_text "$rendered" "replicas: 1"
    require_text "$rendered" "type: ClusterIP"
    require_text "$rendered" "kind: StatefulSet"
    require_text "$rendered" "kind: NetworkPolicy"
    require_text "$rendered" "startupProbe:"
    require_text "$rendered" "readinessProbe:"
    require_text "$rendered" "livenessProbe:"
    require_text "$rendered" "storage: 10Gi"
    require_text "$rendered" "runAsNonRoot: true"
    printf '%s\n' "$rendered" | kubectl create --dry-run=client --validate=false -f - >/dev/null
    printf '[OK] Kafka KRaft manifests passed non-destructive validation.\n'
}

main "$@"
