# ShopSphere Backup & Recovery Guide

> **CRITICAL ARCHITECTURAL WARNING**
> 
> **THE DISASTER RECOVERY PROCEDURES IN THIS DOCUMENT ARE CONFIGURED FOR THE SINGLE-NODE POC ENVIRONMENT.**
> **PRODUCTION COLD-STARTS REQUIRE MULTI-ZONE SNAPSHOTS (REFER TO THE DISASTER RECOVERY ARCHITECTURE DOCUMENT).**

This document outlines the backup, restoration, and data recovery runbooks for the ShopSphere Global Order Platform PoC environment.

---

## 1. PostgreSQL Database Backups

The single physical PostgreSQL server (StatefulSet `postgresql-0` in `shopsphere-data`) holds three logical databases: `customer_db`, `catalogue_db`, and `order_db`.

### 1.1 Scheduled SQL Backup Runbook
To trigger an immediate, complete logical database dump from the running container:
```bash
# Exec into the postgresql container and run pg_dumpall safely
kubectl exec -it postgresql-0 -n shopsphere-data -- pg_dumpall -U postgres > /tmp/shopsphere-all-databases.sql
```
This SQL dump includes schemas, indexes, sequences, table contents, and outbox transactional tables across all three logical contexts.

### 1.2 Schema Restoration Runbook
To restore a backup to a freshly initialized PostgreSQL instance:
```bash
# Overwrite the empty database with your SQL dump file
kubectl exec -i postgresql-0 -n shopsphere-data -- psql -U postgres < /tmp/shopsphere-all-databases.sql
```

---

## 2. Keycloak Realm Configuration Backups

Keycloak stores active OAuth2 clients, credentials password hashing policies, scopes, and user profiles natively inside its relational structure. However, the **Realm Configuration** should be version-controlled independently.

### 2.1 Sanity Export
To export the complete, sanitized `shopsphere` realm metadata securely from Keycloak:
```bash
# Exec into Keycloak and invoke the KcAdmin CLI to export
keycloak_pod=$(kubectl -n shopsphere-platform get pod -l app.kubernetes.io/name=keycloak -o jsonpath='{.items[0].metadata.name}')

kubectl -n shopsphere-platform exec -it "$keycloak_pod" -- \
  /opt/keycloak/bin/kc.sh export --dir /tmp/exported-realm --realm shopsphere
```
The resulting JSON file can be copied out of the container to track client additions or role updates securely inside Git.

---

## 3. Telemetry Configuration Backups

Telemetry rules, alert rules, and Grafana dashboard indexes are version-controlled declaratively as **Kubernetes ConfigMaps** inside the repository under `platform/kubernetes/base/`:

*   **Prometheus Alerting Rules:** Configured in `platform/kubernetes/base/prometheus/prometheus-configmap.yaml`.
*   **Grafana Dashboards:** JSON files stored centrally under `platform/kubernetes/base/grafana/grafana-dashboards-json.yaml`.
*   **Log Forwarding Policies:** Promtail pipelines defined in `platform/kubernetes/base/promtail/promtail-configmap.yaml`.

*Note: If the monitoring namespace is destroyed, re-running `make prometheus-apply` and `make grafana-apply` instantly restores all dashboards, metrics scrapers, and alerting definitions to their correct, validated states.*

---

## 4. Disaster Recovery Testing (PoC Verification)

To verify the restoration process without risking data loss:
1.  **Stage a Backup:** Perform a pg_dumpall.
2.  **Verify Integrity:** Query the file to ensure tables like `products`, `customer_profiles`, and `orders` are fully represented.
3.  **Cold-Start Re-deploy:** Delete the postgresql pod (`kubectl delete pod postgresql-0 -n shopsphere-data`). Since it is managed by a StatefulSet backed by a PersistentVolumeClaim (PVC), the pod automatically reschedules, attaches back to the persistent storage, and recovers to a healthy state without data loss within 30 seconds.
