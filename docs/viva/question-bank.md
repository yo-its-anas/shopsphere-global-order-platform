# ShopSphere Global: Viva Question Bank

This document provides a comprehensive, rigorous question bank designed to prepare candidates for an EduQual Level 6 Capstone Viva examination. It covers 28 architectural, engineering, and operational categories.

> **CRITICAL EXAM RULE:** 
> Always distinguish clearly between the **Implemented Single-Node PoC** and the **Recommended Multi-Zone Production Architecture**.

---

## 1. Software Engineering Principles

### Q1. How did you ensure loose coupling between your microservices?
*   **Concise Strong Answer:** We enforced the Database-per-Service pattern and asynchronous eventing.
*   **Deeper Technical Answer:** We physically prevented foreign key relationships between contexts (e.g., Order and Customer) by assigning each microservice its own logical database schema. Cross-domain data consistency is achieved via Kafka events rather than shared SQL joins.
*   **ShopSphere Example:** The `order_db` references the customer using Keycloak's `subject` UUID string, not a Postgres foreign key to `customer_db`.
*   **Common Follow-up:** *How do you aggregate data if you can't join tables?*
*   **Weak Answer to Avoid:** "We just use the API Gateway to merge data." (Too generic, ignores materialized views or dedicated read-models).

### Q2. How did you enforce the Single Responsibility Principle?
*   **Concise Strong Answer:** By strictly scoping each FastAPI service to a distinct Bounded Context.
*   **Deeper Technical Answer:** Using Clean Architecture, transport layers (`app/api`) only parse JSON, application layers orchestrate use cases, and domain layers execute business rules without knowing about the database.
*   **ShopSphere Example:** `catalogue-service` owns inventory rules. The `order-service` must call the catalogue API to reserve stock; it cannot manipulate stock quantities itself.
*   **Common Follow-up:** *What happens when a requirement crosses multiple boundaries?*
*   **Weak Answer to Avoid:** "We just put it in a shared library." 

---

## 2. Domain-Driven Design

### Q3. Why use a Saga for checkout instead of a distributed transaction?
*   **Concise Strong Answer:** To avoid two-phase commit (2PC) blocking, which destroys microservice scalability.
*   **Deeper Technical Answer:** A Saga coordinates localized transactions. Order service requests a synchronous inventory reservation from Catalogue. If it fails, the local Order transaction aborts. If it succeeds but Order fails later, we publish a compensation event to release the stock.
*   **ShopSphere Example:** Checkout attempts trigger an HTTP `reserve` call to Catalogue, locking the row with `SELECT FOR UPDATE`.
*   **Common Follow-up:** *Why is the reservation synchronous instead of completely asynchronous?*
*   **Weak Answer to Avoid:** "Sagas are always asynchronous." (They can be orchestrated synchronously).

### Q4. What if two customers order the last item simultaneously?
*   **Concise Strong Answer:** The database enforces a sequential row-level lock.
*   **Deeper Technical Answer:** The `catalogue-service` executes a `SELECT ... FOR UPDATE` on the inventory row. The first request acquires the lock, updates the balance, and commits. The second request waits, then reads the updated balance, sees insufficient stock, and fails gracefully.
*   **ShopSphere Example:** The checkout flow returns HTTP 409 Conflict to the second user.
*   **Common Follow-up:** *How does Redis factor into this?*
*   **Weak Answer to Avoid:** "We lock the item in Redis." (Redis is a read-cache here; Postgres is the transactional authority).

---

## 3. Microservices

### Q5. How would you isolate noisy microservices?
*   **Concise Strong Answer:** Through dedicated Node Pools and strict ResourceQuotas.
*   **Deeper Technical Answer:** In production, a CPU-intensive analytics aggregation service would be scheduled onto a distinct GKE Node Pool using taints and tolerations, preventing it from stealing CPU cycles from the critical checkout order-service.
*   **ShopSphere Example:** In the PoC, we enforce Kubernetes `resources.limits` to prevent one service from starving the single shared host VM.
*   **Common Follow-up:** *How do you isolate them at the network layer?*
*   **Weak Answer to Avoid:** "We put them in different folders."

---

## 4. API Design

### Q6. Why idempotency? What if a checkout response times out after the order actually succeeds?
*   **Concise Strong Answer:** It prevents duplicate billing on network retries.
*   **Deeper Technical Answer:** The frontend generates an `Idempotency-Key` (UUID). If the Gateway connection drops *after* the order commits but *before* the client receives the 201 response, the client automatically retries. The backend sees the identical key, skips processing, and returns the cached success payload.
*   **ShopSphere Example:** `POST /api/v1/orders/checkout` requires an Idempotency-Key header.
*   **Common Follow-up:** *Where is the idempotency key stored?*
*   **Weak Answer to Avoid:** "The client remembers not to send it twice."

### Q7. How would payment gateways or mobile apps integrate?
*   **Concise Strong Answer:** Through backend-for-frontend (BFF) edge routing at the API Gateway.
*   **Deeper Technical Answer:** A mobile app hits the API Gateway, which handles rate limiting, payload tailoring, and OIDC token validation. Third-party payment webhooks (e.g. Stripe) would hit a dedicated webhook route on the gateway that validates Stripe signatures before passing to order-service.
*   **ShopSphere Example:** The Gateway translates JWTs and proxies requests transparently.
*   **Common Follow-up:** *How do you secure webhooks without JWTs?*
*   **Weak Answer to Avoid:** "We just trust external payment IPs."

---

## 5. FastAPI

### Q8. Why FastAPI over Django or Flask?
*   **Concise Strong Answer:** High async concurrency, native Pydantic validation, and auto-generated OpenAPI schemas.
*   **Deeper Technical Answer:** FastAPI utilizes ASGI (Starlette), allowing non-blocking I/O during database or API calls, maximizing throughput. Pydantic guarantees strict type safety on JSON payloads, instantly neutralizing injection attacks.
*   **ShopSphere Example:** `async def checkout` releases the thread while waiting for `catalogue-service` to respond.
*   **Common Follow-up:** *When would async actually slow you down?*
*   **Weak Answer to Avoid:** "FastAPI is just newer."

---

## 6. React

### Q9. Why must React communicate only through the API Gateway?
*   **Concise Strong Answer:** To centralize security, CORS, and routing governance.
*   **Deeper Technical Answer:** If React called `analytics-service` directly, we would need to expose every microservice to the public internet, multiplying our attack surface. The Gateway acts as a single ingress choke-point for JWT signature verification.
*   **ShopSphere Example:** The React `ApiClient` sends all traffic to `localhost:8000`.
*   **Common Follow-up:** *Why does React still show static mock KPIs if the backend fails?*
*   **Weak Answer to Avoid:** "React doesn't know how to handle errors."

---

## 7. PostgreSQL

### Q10. Why PostgreSQL? What if PostgreSQL fails?
*   **Concise Strong Answer:** Postgres guarantees ACID transactional safety. If it fails in the PoC, the system halts; in production, Cloud SQL fails over automatically.
*   **Deeper Technical Answer:** We chose Postgres for its robust `NUMERIC` types, row-level locking (`FOR UPDATE`), and JSONB support. In our single-node PoC, a Postgres pod crash halts writes until Kubernetes restarts the pod (seconds). In Production, Google Cloud SQL promotes an active standby in a different zone (minutes) with zero data loss via synchronous replication.
*   **ShopSphere Example:** PoC uses a StatefulSet with a local PVC. Production recommends Cloud SQL HA.
*   **Common Follow-up:** *Why not use NoSQL (MongoDB) for orders?*
*   **Weak Answer to Avoid:** "Postgres is just easier to set up." (Fails to mention ACID requirements for financial data).

---

## 8. SQLAlchemy / Alembic

### Q11. Why use Alembic migrations instead of auto-creating tables on startup?
*   **Concise Strong Answer:** To guarantee deterministic, version-controlled schema evolution.
*   **Deeper Technical Answer:** `metadata.create_all()` is dangerous in production because it cannot handle schema alterations (like dropping a column). Alembic generates sequential SQL scripts, allowing SREs to dry-run DDL changes and ensure safe rollbacks.
*   **ShopSphere Example:** Jenkins runs `alembic upgrade head --sql` to statically validate the migration graph before deploying.
*   **Common Follow-up:** *How do you handle a failed migration?*
*   **Weak Answer to Avoid:** "We just drop the database and restart."

---

## 9. Redis

### Q12. Why Redis? What if Redis is unavailable?
*   **Concise Strong Answer:** Redis provides microsecond cache-aside reads. If it fails, the system degrades gracefully to Postgres.
*   **Deeper Technical Answer:** Redis offloads high-volume read traffic (catalogue searches) from the primary Postgres database. We implemented a Cache-Aside pattern. If Redis crashes (timeout), the application catches the exception, fetches the data from PostgreSQL, and serves the user.
*   **ShopSphere Example:** Product availability fetches check Redis first; on miss or timeout, they query `catalogue_db`.
*   **Common Follow-up:** *Why is Redis NOT the source of truth?*
*   **Weak Answer to Avoid:** "Redis holds the real inventory because it's faster." (Violates ACID durability).

---

## 10. Kafka

### Q13. Why Kafka? What if Kafka goes down after order creation?
*   **Concise Strong Answer:** Kafka handles massive asynchronous event throughput. If it drops, the Transactional Outbox ensures we don't lose the event.
*   **Deeper Technical Answer:** We use Kafka to decouple order creation from downstream tasks (analytics, fulfillment). If the Kafka broker crashes *after* an order is saved, our Transactional Outbox pattern saves the day: the event is stored in Postgres in the same transaction as the order. The outbox publisher retries until Kafka recovers.
*   **ShopSphere Example:** `order_event_outbox` table stores `order.created`.
*   **Common Follow-up:** *Why not RabbitMQ or an API call?*
*   **Weak Answer to Avoid:** "Kafka is just a database."

---

## 11. Keycloak / IAM

### Q14. Why Keycloak?
*   **Concise Strong Answer:** Offloads complex OAuth2/OIDC, password hashing, and RBAC to a dedicated, security-audited provider.
*   **Deeper Technical Answer:** Building custom authentication invites critical CVEs. Keycloak provides standard OIDC flows with PKCE, JWT generation, and centralized user management out-of-the-box.
*   **ShopSphere Example:** The React SPA redirects to Keycloak, retrieves a JWT, and sends it to the API Gateway, which validates the signature locally using cached JWKS.
*   **Common Follow-up:** *Why not use a managed service like Auth0?*
*   **Weak Answer to Avoid:** "Keycloak is the only way to do JWTs."

---

## 12. Docker

### Q15. How does Docker improve your deployment reliability?
*   **Concise Strong Answer:** It ensures absolute environment parity between local development, CI/CD, and production.
*   **Deeper Technical Answer:** We use multi-stage Dockerfiles to compile code and strip away build dependencies, producing lean, secure production images. This eliminates "it works on my machine" errors because the application runs in identical isolated filesystems.
*   **ShopSphere Example:** Our CI pipeline tags images with `ci-${BUILD_NUMBER}` for deterministic rollouts.
*   **Common Follow-up:** *Why not run as root inside Docker?*
*   **Weak Answer to Avoid:** "Docker is a virtual machine."

---

## 13. Kubernetes

### Q16. What happens if a Kubernetes node fails?
*   **Concise Strong Answer:** In the PoC, the system dies. In production GKE, pods are rescheduled to healthy nodes.
*   **Deeper Technical Answer:** Our PoC is a single-node `kind` cluster. If the underlying GCP VM dies, everything stops. In our Recommended Production Architecture, GKE automatically detects the node failure. The Kubernetes Scheduler reschedules the stateless pods onto surviving nodes in other Availability Zones.
*   **ShopSphere Example:** We use `Deployments` with `replicas` to ensure Kubernetes actively monitors and replaces crashed pods.
*   **Common Follow-up:** *How do you perform zero-downtime deployment?*
*   **Weak Answer to Avoid:** "We just restart the server quickly."

### Q17. How would you perform zero-downtime deployment?
*   **Concise Strong Answer:** Using Kubernetes Rolling Updates with readiness probes.
*   **Deeper Technical Answer:** When deploying a new image, Kubernetes spins up a new pod. It waits for the `/health/ready` endpoint to return HTTP 200. Only then does it add the new pod to the Service load balancer and terminate an old pod, ensuring zero dropped requests.
*   **ShopSphere Example:** API Gateway routes traffic only to pods passing the readiness probe.

---

## 14. Terraform / IaC

### Q18. Why use Terraform?
*   **Concise Strong Answer:** To define infrastructure as version-controlled, reproducible code.
*   **Deeper Technical Answer:** Terraform ensures our GCP firewall rules, VM instances, and VPC networks are declared immutably. If the infrastructure drifts, `terraform plan` detects it. 
*   **ShopSphere Example:** We statically validate Terraform formatting and syntax in Jenkins.
*   **Common Follow-up:** *Where is your state file stored securely?*
*   **Weak Answer to Avoid:** "We just use Terraform to run bash scripts."

---

## 15. Jenkins / CI/CD

### Q19. Describe your CI/CD flow. What happens on failure?
*   **Concise Strong Answer:** Code push triggers a 23-stage pipeline verifying quality, security, and deployment. On failure, we rollback automatically.
*   **Deeper Technical Answer:** The Jenkinsfile executes Pytest, SAST (Semgrep), SCA (Trivy), and OPA checks. If a Kustomize deployment fails the `rollout status` check, the `post.failure` block executes `kubectl rollout undo`, instantly restoring the cluster to the last known healthy state.
*   **ShopSphere Example:** Jenkins runs directly on port 8082, executing containerized scanners.
*   **Common Follow-up:** *Why not use GitHub Actions?*
*   **Weak Answer to Avoid:** "Jenkins is the only CI tool that works with Kubernetes."

---

## 16. DevSecOps

### Q20. Why Trivy plus Semgrep plus Bandit?
*   **Concise Strong Answer:** They provide defense-in-depth across different attack surfaces (OS, Architecture, and Code).
*   **Deeper Technical Answer:** Bandit looks for Python-specific flaws (like hardcoded secrets). Semgrep searches the entire monorepo for advanced architectural anti-patterns. Trivy scans the compiled Docker image filesystem for vulnerable OS-level packages (CVEs). 
*   **ShopSphere Example:** A CRITICAL Trivy finding will fail the Jenkins pipeline before the image is loaded into `kind`.
*   **Common Follow-up:** *Why OPA?*
*   **Weak Answer to Avoid:** "One scanner catches everything."

### Q21. Why OPA (Open Policy Agent)?
*   **Concise Strong Answer:** To enforce Policy-as-Code on Kubernetes manifests.
*   **Deeper Technical Answer:** OPA evaluates rendered Kustomize YAML against Rego rules. It actively blocks deployments that attempt to run as `privileged: true` or without Resource Limits, protecting cluster integrity.

---

## 17. Automated Testing

### Q22. How do you ensure tests are reliable?
*   **Concise Strong Answer:** By isolating dependencies and avoiding shared mutable state.
*   **Deeper Technical Answer:** Our Pytest suites use fresh, isolated SQLite/Postgres schemas or mocked repositories per test run. We strictly separate Unit tests (mocked dependencies) from Integration tests (live database/Keycloak connections).
*   **ShopSphere Example:** The dashboard integration test mocks the `useDashboardApi` hook to deterministically verify React UI rendering.
*   **Common Follow-up:** *Why do you mock Keycloak in some tests but not others?*
*   **Weak Answer to Avoid:** "We just test it in production."

---

## 18. Security

### Q23. Defend your Network Boundaries.
*   **Concise Strong Answer:** We enforce a zero-trust, private network architecture.
*   **Deeper Technical Answer:** Databases and microservices have no public IPs; they communicate exclusively via internal Kubernetes `ClusterIPs`. External traffic is explicitly forced through the API Gateway on port 8000. 
*   **ShopSphere Example:** NetworkPolicies explicitly block the catalogue-service from querying the order_db directly.
*   **Common Follow-up:** *How do you manage secrets?*
*   **Weak Answer to Avoid:** "We keep passwords in a hidden folder."

---

## 19. Monitoring / Observability

### Q24. Why Prometheus plus Loki? What does OpenTelemetry provide without Tempo?
*   **Concise Strong Answer:** Prometheus handles numerical metrics; Loki handles structured logs; OTEL propagates trace context.
*   **Deeper Technical Answer:** Prometheus scrapes `/metrics` to generate alarms (e.g. error rate > 5%). Loki stores unstructured text streams to diagnose *why* the error happened. OpenTelemetry middleware injects `traceparent` headers, mapping the request across services. Even without a UI like Tempo in the PoC, the OTEL headers ensure logs in Loki share a unified `correlation_id`.
*   **ShopSphere Example:** API Gateway generates a Correlation ID, which is printed in order-service Loki logs.
*   **Common Follow-up:** *How does Prometheus know a pod died?*
*   **Weak Answer to Avoid:** "Loki reads the metrics."

---

## 20. Wazuh

### Q25. Why Wazuh? State your PoC scope honestly.
*   **Concise Strong Answer:** It provides an active Security Information and Event Management (SIEM) capability.
*   **Deeper Technical Answer:** Wazuh provides intrusion detection, File Integrity Monitoring (FIM), and Vulnerability Assessment. In our PoC, it is sandboxed as a Kubernetes DaemonSet, meaning it successfully monitors container-level anomalies (like touching `/etc/`) but does not have root visibility into the parent GCP host VM.
*   **ShopSphere Example:** FIM correctly registered an alert when we modified an internal configuration file during validation.
*   **Common Follow-up:** *How would you deploy Wazuh in production?*
*   **Weak Answer to Avoid:** "Wazuh protects our network from DDoS." (It's a host/log SIEM, not a WAF).

---

## 21. Performance

### Q26. How did you validate performance?
*   **Concise Strong Answer:** Through an asynchronous, controlled Python/k6 baseline load test.
*   **Deeper Technical Answer:** We generated concurrent simulated traffic against the API Gateway, capturing latency percentiles ($p_{50}$, $p_{95}$). We observed catalog reads averaging 15ms due to Redis caching, and proved that concurrent checkouts on empty carts gracefully returned HTTP 400s without crashing the pod.
*   **ShopSphere Example:** `tests/performance/performance_report.md` documents the empirical latencies.
*   **Common Follow-up:** *Why didn't you run a 10,000 requests-per-second test?*
*   **Weak Answer to Avoid:** "We just guessed the performance."

---

## 22. Failure Scenarios

### Q27. What happens if the VM dies? Why doesn't your PoC provide HA?
*   **Concise Strong Answer:** The PoC system will go completely offline. We intentionally traded physical HA for resource efficiency.
*   **Deeper Technical Answer:** The PoC is a single-node sandbox. It shares a single CPU, memory pool, and disk. A VM crash causes total failure. This is documented explicitly as a PoC limitation. Production HA requires multi-zone GKE, Cloud SQL, and Load Balancers.
*   **ShopSphere Example:** Documented under *Scaling for Millions* and *Disaster Recovery* strategies.
*   **Common Follow-up:** *What if a Kubernetes pod fails instead of the VM?*
*   **Weak Answer to Avoid:** "The system is perfectly highly available." (Dishonest).

---

## 23. Architecture Trade-offs

### Q28. Why not use GKE for the PoC?
*   **Concise Strong Answer:** Cost, time-to-provision, and educational focus.
*   **Deeper Technical Answer:** GKE introduces significant financial overhead (control plane fees, multi-zone network egress). Using `kind` on a single VM allowed us to validate 100% of our Kubernetes manifests, NetworkPolicies, and DevSecOps pipelines identically to production, without burning cloud budget on idle multi-node clusters.
*   **ShopSphere Example:** The exact same Kustomize manifests can be applied to GKE tomorrow.
*   **Common Follow-up:** *When WOULD you move to GKE?*
*   **Weak Answer to Avoid:** "GKE is too hard to use."

---

## 24. Production Migration

### Q29. When would you move to GKE?
*   **Concise Strong Answer:** When the business requires horizontal host scaling, zero-downtime node upgrades, and zone-failure survival.
*   **Deeper Technical Answer:** When user traffic exceeds the capacity of a single GCP VM, or when business SLAs mandate High Availability (HA). GKE provides automated node provisioning (Cluster Autoscaler) and distributes pods across physical datacenters.
*   **ShopSphere Example:** Phase 2 of our Migration Strategy decouples state to Managed Cloud SQL and compute to GKE.
*   **Common Follow-up:** *What is the hardest part of that migration?*
*   **Weak Answer to Avoid:** "We just copy the code over."

---

## 25. Scaling to Millions

### Q30. How would you handle 10 million users?
*   **Concise Strong Answer:** Edge caching, stateless horizontal scaling, and managed data sharding.
*   **Deeper Technical Answer:** We would utilize Cloud CDN to absorb $90\%$ of static/catalog read traffic. API Gateway and microservices would scale horizontally via HPA. The database tier would utilize Cloud SQL Read Replicas for queries, and Kafka would be partitioned heavily to process asynchronous orders in parallel.
*   **ShopSphere Example:** Redis already implements the cache-aside pattern to protect the Postgres master.
*   **Common Follow-up:** *What becomes the bottleneck at 10 million users?*
*   **Weak Answer to Avoid:** "We just buy a bigger VM."

---

## 26. International Expansion

### Q31. How would you support Europe and Asia? What about GDPR/data residency?
*   **Concise Strong Answer:** Regional GKE deployments and localized database clusters.
*   **Deeper Technical Answer:** We would deploy active GKE clusters in EU and APAC regions, routed via Global Anycast Cloud Load Balancing. To satisfy GDPR, EU customer profiles must reside strictly in an EU-hosted PostgreSQL instance.
*   **ShopSphere Example:** We utilize string subjects instead of foreign keys, allowing us to shard customer identities to regional databases without breaking order histories.
*   **Common Follow-up:** *How do you keep the global catalog synchronized?*
*   **Weak Answer to Avoid:** "We just put all the data in America."

---

## 27. Disaster Recovery

### Q32. How would DR work? What are your RPO/RTO targets?
*   **Concise Strong Answer:** An Active-Passive (Warm Standby) architecture targeting a 5-minute RPO and 2-hour RTO.
*   **Deeper Technical Answer:** We maintain a scaled-down GKE cluster in a secondary region. Cloud SQL replicates asynchronously. If the primary region fails, we accept up to 5 minutes of data loss (RPO) to avoid the extreme latency of synchronous global commits. We promote the database, scale the pods, and update DNS within 2 hours (RTO).
*   **ShopSphere Example:** Documented in `disaster-recovery.md`.
*   **Common Follow-up:** *Why not promise zero data loss?*
*   **Weak Answer to Avoid:** "Our system never loses data." (Physically impossible across regions without massive latency).

---

## 28. Standards/Frameworks

### Q33. How does ShopSphere align with ISO 27001 and NIST SSDF?
*   **Concise Strong Answer:** Through strict access controls, cryptography, and automated shift-left security pipelines.
*   **Deeper Technical Answer:** We consider ISO 27001 by enforcing JWT signature validation (Cryptography) and namespace NetworkPolicies (Network Security). We align with NIST SSDF by incorporating Bandit, Semgrep, and Trivy directly into the Jenkins pipeline to detect and block vulnerabilities before deployment.
*   **ShopSphere Example:** The pipeline physically halts if a Critical CVE is found, proving automated compliance enforcement.
*   **Common Follow-up:** *Are you officially certified?*
*   **Weak Answer to Avoid:** "Yes, we are fully ISO certified." (It is a PoC; you cannot claim formal legal certification).
