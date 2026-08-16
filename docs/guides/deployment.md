# ShopSphere PoC Deployment Guide

This document defines the deployment runbook for the ShopSphere Global Order Platform PoC environment. 

## 1. Single-Node Scope Disclaimer
This guide applies **only to the local single-node `kind-shopsphere-poc` sandbox VM**. It does **not** deploy a high-availability (HA), multi-zone, production-grade cluster. Replicated database nodes, redundant network ingress routes, separate telemetry nodes, and managed SIEM servers must be provisioned separately using production-reference guides.

---

## 2. Automated Jenkins Deployment (Recomended CI/CD)

The absolute safest and most robust way to deploy or update the PoC environment is by running the **automated 23-stage Jenkins pipeline** on the `main` branch. 

### 2.1 The Automated Pipeline Workflow:
1.  **Software Quality Gates:** Runs static style (`Black`), syntax (`Ruff`), and security linting (`Bandit`, `Semgrep`) across all code bases.
2.  **Container Build:** Generates optimized Docker containers for all services and the React frontend, tagging them securely with `ci-${BUILD_NUMBER}`.
3.  **Vulnerability Scan:** Scans the build containers recursively with `Trivy` to block CVE leakage.
4.  **Policy as Code:** Validates Kustomize manifests against `Open Policy Agent` Rego policies (`security.rego`) to block privileged pods or root escalation.
5.  **Kind Loading:** Automatically transfers the built images directly into the local `kind` cluster via `./platform/kind/load-images.sh`.
6.  **Kustomize Apply:** Dynamically patches the overlay configurations with the new image tags and rolls out the changes:
    ```bash
    kubectl apply -k platform/kubernetes/overlays/poc
    ```
7.  **Rollout Health Check:** Executes `kubectl rollout status` sequentially on all core microservices and gateways to monitor readiness.
8.  **Automated Rollback Policy:** In case any service fails to roll out within 180 seconds or throws crash loop errors, the pipeline catches the failure under `post.failure` and executes a safe, non-destructive **rollout undo** to restore the previous stable cluster state instantly:
    ```bash
    kubectl rollout undo deployment/api-gateway -n shopsphere-apps
    kubectl rollout undo deployment/customer-service -n shopsphere-apps
    kubectl rollout undo deployment/catalogue-service -n shopsphere-apps
    kubectl rollout undo deployment/order-service -n shopsphere-apps
    kubectl rollout undo deployment/analytics-service -n shopsphere-apps
    kubectl rollout undo deployment/frontend -n shopsphere-apps
    ```

---

## 3. Manual Bootstrap Runbook (Local Verification)

For manual SRE diagnostics or cluster cold-starts, execute commands recursively using the project `Makefile`:

### 3.1 Step 1: Base Kind Cluster Cold-Start
Verify or spin up the underlying Kubernetes container node:
```bash
./platform/kind/create-cluster.sh
```

### 3.2 Step 2: Database and State Platform Bootstrap
Deploy the centralized datastores, generate credential Secrets, and configure database permissions:
```bash
make postgresql-secret
make validate-postgresql
make postgresql-apply
make postgresql-status
make redis-secret
make redis-apply
make redis-status
```

### 3.3 Step 3: Event Broker & Keycloak Identity Bootstrap
Deploy Kafka and Keycloak, bootstrap the `shopsphere` realm, and register OAuth clients:
```bash
make validate-kafka
make kafka-apply
make kafka-topics
make kafka-status

make keycloak-secret
make validate-keycloak
make keycloak-apply
make keycloak-configure
make keycloak-status
```

### 3.4 Step 4: Core Microservices Rollout
Build, load, and deploy first-party services sequentially:
```bash
# 1. customer-service
make customer-service-secret
make customer-service-apply

# 2. catalogue-service
make catalogue-service-secret
make catalogue-service-apply

# 3. order-service
make order-service-identity
make order-service-apply

# 4. analytics-service (Dashboard Engine)
make analytics-service-apply

# 5. api-gateway (Single Ingress Controller)
make api-gateway-apply
```

---

## 4. Post-Deployment Verification (SRE Checks)

Verify that the entire platform is running in a fully healthy, ready state:

```bash
# Verify pod states across all namespaces
kubectl get pods,deployments,daemonsets -A

# Query the centralized operations dashboard directly to verify API Gateway + Prometheus integration
# 1. Port forward the API Gateway
kubectl -n shopsphere-apps port-forward svc/api-gateway 8000:8000 &
# 2. Port forward Keycloak to fetch token
kubectl -n shopsphere-platform port-forward svc/keycloak 8080:8080 &

# 3. Fetch token and query operations health
TOKEN=$(curl -s -d "client_id=shopsphere-frontend" -d "username=operations@yopmail.com" -d "password=TestPassword@1234" -d "grant_type=password" "http://localhost:8080/realms/shopsphere/protocol/openid-connect/token" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/operations/dashboard
```

The JSON response must report `api_availability: 100.0` and `healthy_service_count: 4` with no degraded or unavailable dependencies.
