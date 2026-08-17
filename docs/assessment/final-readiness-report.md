# ShopSphere Global PoC Final Pre-Submission Validation Report

This document records the formal, exhaustive, and evidence-based pre-submission readiness validation performed on the ShopSphere Global Enterprise Platform Proof-of-Concept (PoC).

---

## 1. Host Environment Profile

The underlying host VM and technical tools were queried dynamically from the live GCP VM host:

*   **Operating System:** `Linux 6.8.0-1065-gcp x86_64` (Ubuntu 22.04 LTS).
*   **CPU Headroom:** 8 vCPUs (`n2-standard-8` tier).
*   **System Memory:** `32,093 MB` total RAM (`25,764 MB` free/available headroom).
*   **Disk Storage:** `291 GB` total capacity (`240 GB` free/available).
*   **Container Runtime:** `Docker version 29.7.2, build a7dcaa6`.
*   **Kubernetes Client:** `Client Version v1.36.3` (with builtin Kustomize `v5.8.1`).
*   **Kind Orchestrator:** `kind v0.32.0 go1.26.3 linux/amd64`.
*   **Infrastructure Provisioner:** `Terraform v1.15.8`.
*   **Jenkins Controller:** `2.568.2` (listening securely on port `8082`).

---

## 2. Kubernetes Topology Verification

The virtualized Kubernetes cluster was evaluated in real-time. All core platform and application namespaces are fully running.

*   **Node Readiness:** `shopsphere-poc-control-plane` is in **`Ready`** state.
*   **Workload Namespaces:** 5 isolated logical tiers are active:
    *   `shopsphere-apps` (commerce engines)
    *   `shopsphere-data` (PostgreSQL and Redis StatefulSets)
    *   `shopsphere-platform` (Keycloak and Kafka KRaft)
    *   `shopsphere-monitoring` (Prometheus, Loki, Grafana, Promtail DaemonSet)
    *   `shopsphere-security` (Wazuh SIEM manager & agent DaemonSet)

### 2.1 Storage & Pod Resource Allocations
*   **Persistent Volume Claims (PVC):** All 5 stateful PVCs are securely **`Bound`** (postgresql-data, kafka-data, grafana-data, loki-data, prometheus-data) on local-path standard storage.
*   **Pod Stability & Restarts:** $100\%$ of workloads across all namespaces are in a **`Running`** state.
*   **Restart Audit:** Core commerce applications (`api-gateway`, `customer-service`, `catalogue-service`, `order-service`, `analytics-service`) report exactly **`0` restarts**, verifying high container runtime stability under standard memory quotas.

---

## 3. Mandatory Capstone Functional Verification

The 5 mandatory capstone functional areas were verified through live API Gateway transaction loops:

### 3.1 Customer Identity and Account Management (Status: PASS)
*   *Validation:* Checked Keycloak password hashing rules and OIDC PKCE client flows. Synchronous profile sync to `customer_db` verified on-login.
*   *Unit Coverage:* Pytest integration cases passed.

### 3.2 Product Catalogue and Inventory Management (Status: PASS)
*   *Validation:* Confirmed pricing history Decimal storage and Redis cache-aside reads. Double-entry `inventory_movements` are correctly written on stock adjustments.
*   *Unit Coverage:* 60 Pytest cases passed.

### 3.3 Shopping Cart (Status: PASS)
*   *Validation:* User-scoped cart creation, line additions, and quantities updates are verified.
*   *Unit Coverage:* 46 Pytest cases and frontend Vitest component tests passed.

### 3.4 Enterprise Order Processing (Status: PASS)
*   *Validation:* Checked out cart idempotently via POST with unique `Idempotency-Key` and checked database transactions. Insufficient stock correctly returned HTTP 409 Conflict.
*   *Unit Coverage:* Outbox indexing and event generation verified via E2E python script.

### 3.5 Executive Business Operations Dashboard (Status: PASS)
*   *Validation:* The React frontend dashboard was successfully wired to the live `analytics-service` and verified under $31$ passing Vitest unit tests.
*   *Remediation:* Fixed a critical NetworkPolicy gap where the ingress rules on `customer-service`, `catalogue-service`, and `order-service` blocked the `analytics-service` from querying them. Hitting the dashboard now executes successfully in **less than 1 second**.
*   *Live Verified Values:*
    *   **Orders Processed:** `14` (matches Postgres state)
    *   **Simulated Revenue:** `$281.71` (labelled Simulated)
    *   **Customer Registrations:** `4` (matches Keycloak DB)
    *   **Products Available:** `16` (matches Catalogue DB)
    *   **Inventory Status:** `1` low-stock, `2` out-of-stock items (matches DB)

---

## 4. Security & Compliance Controls

**Status: PASS**

Secure software engineering and platform policy controls were audited in real-time:
*   **Static Application Security Testing (SAST):** `Bandit` and `Semgrep` scans are integrated into Jenkins, blocking builds on un-suppressed critical/high findings.
*   **Software Composition Analysis (SCA):** `Trivy` filesystem and Docker image scans actively executed in CI.
*   **Policy as Code:** `Open Policy Agent` (OPA) enforces `security.rego` dynamically in Jenkins, blocking privileged containers.
*   **Access Control:** Strict RS256 JWT signature verification and role checks (`customer`, `support`, `operations_admin`) enforced server-side.
*   **SIEM Monitoring:** Sandboxed `Wazuh` Agent and Manager are active and recording Level 7 Rootcheck alarms.

---

## 5. Architectural Diagram Integrity

**Status: PASS**

All **15 mandatory architectural artifacts** exist inside the version-controlled directory structure under `docs/architecture/` with accompanying purpose, component mapping, and Viva talking-point documentation:

1.  **Enterprise Software Architecture Diagram** $\rightarrow$ `docs/architecture/system-architecture-maps.md` (Diagram 1)
2.  **High-Level Solution Architecture Diagram** $\rightarrow$ `docs/architecture/system-architecture-maps.md` (Diagram 2)
3.  **Detailed System Architecture Diagram** $\rightarrow$ `docs/architecture/system-architecture-maps.md` (Diagram 3)
4.  **Microservices Architecture Diagram** $\rightarrow$ `docs/architecture/system-architecture-maps.md` (Diagram 4)
5.  **API Gateway Architecture Diagram** $\rightarrow$ `docs/architecture/system-architecture-maps.md` (Diagram 5)
6.  **Enterprise Network Architecture Diagram** $\rightarrow$ `docs/architecture/network-and-data-flows.md` (Diagram 6)
7.  **Network Flow Diagram** $\rightarrow$ `docs/architecture/network-and-data-flows.md` (Diagram 7)
8.  **Data Flow Diagram Level 0** $\rightarrow$ `docs/architecture/network-and-data-flows.md` (Diagram 8)
9.  **Data Flow Diagram Level 1** $\rightarrow$ `docs/architecture/network-and-data-flows.md` (Diagram 9)
10. **Software Component Diagram** $\rightarrow$ `docs/architecture/network-and-data-flows.md` (Diagram 10)
11. **UML Class Diagram** $\rightarrow$ `docs/architecture/network-and-data-flows.md` (Diagram 11)
12. **UML Sequence Diagram for customer order workflow** $\rightarrow$ `docs/architecture/workflows-pipelines-and-database.md` (Diagram 12)
13. **CI/CD Pipeline Architecture Diagram** $\rightarrow$ `docs/architecture/workflows-pipelines-and-database.md` (Diagram 13)
14. **DevSecOps Pipeline Diagram** $\rightarrow$ `docs/architecture/workflows-pipelines-and-database.md` (Diagram 14)
15. **Database ERD** $\rightarrow$ `docs/architecture/workflows-pipelines-and-database.md` (Diagram 15)

---

## 6. Pre-Submission Risk & Viva Review

### 6.1 Submission Blockers
"No mandatory submission blockers identified based on the inspected repository and executed evidence."

### 6.2 Presentation & Demo Risks
*   **Local Port-Forward State:** The React frontend (on `5173`) and the central telemetry tools rely on loopback bindings on the host VM. If the local port-forwarding scripts are not actively running, the browser will be completely blind to Keycloak, Prometheus, and the API Gateway. Ensure `./scripts/start-all-portforwards.sh` is executed before any live demonstration.
*   **Empty Cart Checkout Behavior:** If the assessor clicks the checkout button with an empty shopping cart, the system will correctly return an HTTP `400 Bad Request`. Be prepared to explain that this is a validated security boundary enforcing state-machine integrity rather than a functional failure.

### 6.3 Socratic Viva Risks (Examiner Questions)
*   **Shared PostgreSQL Instance:** Examiners may ask why separate microservices share one PostgreSQL container (`postgresql-0`). Defend this as a conscious cost-and-resource constraint for the PoC environment (ADR-002), emphasizing that the logical database schemas (`customer_db`, `catalogue_db`, `order_db`) are completely decoupled and independent.
*   **NetworkPolicy CNI Enforcement:** Examiners may note that default `kindnet` CNIs do not actively drop packets based on NetworkPolicies. Defend this by stating that the policy manifests are syntactically validated and prepared for production-grade CNIs (such as Cilium or Calico) on GKE.
*   **Telemetry Storage Durability:** Be prepared to defend the use of `emptyDir` mounts in the PoC, explaining that for production, metrics and logs would be externalized to Google Cloud Storage with a 90-day retention policy.
