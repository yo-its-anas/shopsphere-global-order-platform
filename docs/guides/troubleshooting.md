# ShopSphere Platform Troubleshooting Guide

This guide provides step-by-step diagnostic and remediation runbooks for common platform, network, and application failures within the ShopSphere single-node PoC environment.

---

## 1. Network Issues & Connection Failures

### 1.1 "Connection Refused" on local port forwarding
*   **Symptom:** Running local requests or opening dashboards in your browser returns a connection refused error.
*   **Diagnostic:** Check if the port-forwarding daemons or the frontend Node server are actively listening on the host VM loopback address (`127.0.0.1`):
    ```bash
    sudo ss -tulpn | grep -E '5173|8000|8080|8081|3000|9090|3100'
    ```
*   **Remediation:** If the sockets are empty, restart all port-forwards and the frontend dev server simultaneously in the background:
    ```bash
    ./scripts/start-all-portforwards.sh
    ```

### 1.2 "Keycloak Account is not fully set up" or login errors
*   **Symptom:** Logging in via the frontend redirects to Keycloak but fails with `invalid_grant` or account errors.
*   **Diagnostic:** This occurs if a user was created without email verification, contains mandatory outstanding actions (like UPDATE_PASSWORD), or if the password violates realm password complexity rules.
*   **Remediation:** Reset the user's password and remove mandatory actions:
    ```bash
    # Exec into keycloak pod and force non-temporary password
    kubectl exec -it keycloak-0 -n shopsphere-platform -- /bin/bash
    /opt/keycloak/bin/kcadm.sh config credentials --server http://127.0.0.1:8080 --realm master --user <ADMIN_USER> --password <ADMIN_PASSWORD>
    
    # 1. Update emailVerified to true and remove required actions
    /opt/keycloak/bin/kcadm.sh update users/<user_id> -r shopsphere -s emailVerified=true -s requiredActions=[]
    # 2. Reset password to a compliant value
    /opt/keycloak/bin/kcadm.sh set-password -r shopsphere --username <username> --new-password <compliant_password> --temporary=false
    ```

---

## 2. Kubernetes Failures & Pod Restarts

### 2.1 Pods stuck in `Pending` or `CrashLoopBackOff`
*   **Symptom:** Running `kubectl get pods -A` reveals pods in non-running states.
*   **Diagnostic:**
    1.  **Pending:** Check if the pod exceeds namespace ResourceQuotas or if the cluster is out of memory:
        ```bash
        kubectl describe pod <pod_name> -n <namespace>
        ```
    2.  **CrashLoopBackOff:** Inspect the container stdout logs to identify internal application exceptions (e.g., database connection refused):
        ```bash
        kubectl logs <pod_name> -n <namespace> --tail=50
        ```
*   **Remediation:**
    *   *Resource Quotas:* If a LimitRange is violated, adjust requests/limits in the deployment overlay.
    *   *Database Refused:* Ensure PostgreSQL is fully ready (`kubectl get pods -n shopsphere-data`). If it is restarting, check its storage claims.

---

## 3. Database & Database Migration Conflicts

### 3.1 "TypeError: can't compare offset-naive and offset-aware datetimes" during sorting
*   **Symptom:** Hitting `/api/v1/customers/me/activity` or running Python unit tests throws a fatal datetime sorting exception.
*   **Root Cause:** Occurs when attempting to sort merged lists containing naive datetimes (loaded from database SQLite/Postgres schemas) and aware datetimes (Keycloak identity log payloads).
*   **Remediation:** Force all compared timestamps to be timezone-aware (specifically UTC) on-the-fly before sorting. Refer to the patched `customer_accounts.py` logic:
    ```python
    from datetime import timezone
    merged = sorted(..., key=lambda item: item.timestamp.astimezone(timezone.utc) if item.timestamp.tzinfo else item.timestamp.replace(tzinfo=timezone.utc))
    ```

### 3.2 Database schema locks or migrations out of sync
*   **Symptom:** Microservices fail to start, reporting Alembic migration mismatches or locked DDL transactions.
*   **Diagnostic:** Check current migration heads against the database:
    ```bash
    cd services/<service>
    .venv/bin/alembic current
    ```
*   **Remediation:** Re-run database schema upgrade offline using PostgreSQL credentials or manually stamp a migration version if it was already applied:
    ```bash
    .venv/bin/alembic stamp head
    ```

---

## 4. Observability & SIEM Failures

### 4.1 Operations Dashboard times out with 504 "upstream_timeout"
*   **Symptom:** Querying `/api/v1/operations/dashboard` through the API Gateway fails or takes too long.
*   **Diagnostic:** This occurs if the `analytics-service` is blocked from querying Prometheus at `prometheus.shopsphere-monitoring.svc.cluster.local:9090` due to a NetworkPolicy mismatch.
*   **Remediation:** Apply the patched Prometheus Ingress NetworkPolicy allowing TCP egress from `shopsphere-apps` namespace (labeled `shopsphere.io/tier: applications`) to port 9090:
    ```bash
    kubectl apply -f platform/kubernetes/base/prometheus/network-policy.yaml
    ```
