# Order Processing Administration Guide

This runbook defines the operational and administrative procedures for managing, troubleshooting, and diagnosing the ShopSphere Enterprise Order Processing Engine and Observability capabilities.

---

## 1. Identity & Role Management (Keycloak)

System operations are strictly governed by Keycloak Role-Based Access Control (RBAC). No administrative account may impersonate a customer or query transactional databases directly.

*   **`customer`:** Managed natively via OIDC. Governs cart creation, profile management, and viewing personal order history under `/api/v1/orders/me`.
*   **`support`:** Granted read-only permissions to inspect any customer's order history, status timeline, and safe transaction audit trails under `/api/v1/admin/orders`. Blocked from modifying order states.
*   **`operations_admin`:** Granted write permissions to issue state transitions (`CONFIRMED → PROCESSING → FULFILLED`) and authorize eligible order cancellations.

### 1.1 Managing Operational Users (Admin CLI)
To list, create, or assign roles to support or administrative personnel inside the Kind cluster:
```bash
# 1. Exec into the Keycloak pod
keycloak_pod=$(kubectl -n shopsphere-platform get pod -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')
kubectl -n shopsphere-platform exec -it "$keycloak_pod" -- bash

# 2. Login to admin-cli
kcadm=/opt/keycloak/bin/kcadm.sh
"$kcadm" config credentials --server http://127.0.0.1:8080 --realm master --user <ADMIN_USER> --password <ADMIN_PASSWORD>

# 3. Add operations_admin role to an existing user
"$kcadm" add-roles -r shopsphere --uusername staff@yopmail.com --rolename operations_admin
```

---

## 2. Telemetry & Outbox Diagnosis

### 2.1 Checking Transactional Outbox (PostgreSQL)
Both the `catalogue-service` and `order-service` utilize the **Transactional Outbox Pattern** to ensure at-least-once message delivery to Kafka without distributed transactions.

If events are not appearing in downstream consumers:
```bash
# Query pending/unpublished events in the order-service outbox
kubectl -n shopsphere-data exec -it postgresql-0 -- psql -U postgres -d order_db -c \
  "SELECT id, event_type, processed, created_at FROM order_event_outbox WHERE processed = false LIMIT 10;"
```
If processed is `false`, the outbox publisher daemon (worker) inside the order-service container is either restarting or blocked. Check its pod logs:
```bash
kubectl -n shopsphere-apps logs -l app.kubernetes.io/name=order-service -c outbox-publisher --tail=50
```

### 2.2 Verifying Kafka Consumer Offsets
To ensure consumer pods are actively reading topics and are not lagging:
```bash
# Exec into the Kafka broker pod
kafka_pod=$(kubectl -n shopsphere-platform get pod -l app.kubernetes.io/name=kafka -o jsonpath='{.items[0].metadata.name}')
kubectl -n shopsphere-platform exec -it "$kafka_pod" -- /bin/bash

# Check consumer group details and active lag
/opt/kafka/bin/kafka-consumer-groups.sh --bootstrap-server localhost:9092 --describe --group order-consumers
```

---

## 3. Executive Operations Dashboard Diagnostics

The Executive Operations Dashboard (`GET /api/v1/operations/dashboard`) aggregates live telemetry from Prometheus and state databases. 

### 3.1 Troubleshooting Missing Dashboard Metrics ("Service metrics not found")
If the dashboard reports `AvailabilityState.UNKNOWN` or "Service metrics not found" for first-party applications:
1.  **Verify Prometheus Scraping:** Connect to Prometheus and verify targets are `UP`:
    ```bash
    kubectl -n shopsphere-monitoring exec -it prometheus-<pod_id> -- curl http://localhost:9090/api/v1/targets
    ```
2.  **Verify NetworkPolicy Ingress:** Ensure the `prometheus-ingress` policy permits TCP traffic from the applications namespace on port `9090` (refer to the patched `platform/kubernetes/base/prometheus/network-policy.yaml` configuration).
3.  **DNS Failures:** Check DNS resolution from within the `analytics-service` container:
    ```bash
    kubectl exec -n shopsphere-apps deploy/analytics-service -- nslookup prometheus.shopsphere-monitoring.svc.cluster.local
    ```

---

## 4. Operational Boundaries under Single-Node Topology

SRE personnel must recognize that this PoC environment is a single-node virtualization sandbox:
*   **Shared Failure Domain:** High CPU/Memory usage by logging or Kafka components directly degrades the database query performance of core commerce.
*   **I/O Throttling:** High-volume load tests cause immediate PostgreSQL lock contention and disk I/O bottlenecks.
*   **No High Availability:** The cluster improves service restart times but cannot survive a physical host VM crash. Disaster-recovery, backups, and off-cluster long-term retention of audit events must be handled by GCP/Cloud-native architectures in production.
