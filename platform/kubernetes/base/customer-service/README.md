# Customer Service Kubernetes Base

Defines the internal customer-service Deployment, ClusterIP Service, and intended network boundary. The workload runs as UID/GID `10001`, drops all Linux capabilities, does not mount a service-account token, and uses the runtime-default seccomp profile.

The application and migration containers use a read-only root filesystem. A size-limited, memory-backed `/tmp` volume is the only writable path and accommodates safe runtime temporary-file needs. Alembic runs as an init container; a production platform should normally execute migrations as a separately controlled release operation.

Ingress is intended only from pods labelled `app.kubernetes.io/name=api-gateway`. Egress is limited to cluster DNS, PostgreSQL, and Keycloak. Kubernetes `NetworkPolicy` enforcement depends on the installed CNI. The default kind networking configuration may not enforce these rules; use a NetworkPolicy-capable CNI and verify enforcement before treating the policy as a security boundary.

One replica is intentional for the single-node PoC. Increasing pod replicas on the same kind node and physical VM does not provide host-level high availability.

