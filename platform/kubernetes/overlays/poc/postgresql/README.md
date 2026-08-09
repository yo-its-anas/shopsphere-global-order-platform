# PostgreSQL PoC Persistence

This overlay deploys one PostgreSQL 16 instance into `shopsphere-data` for the customer-service and Keycloak logical databases. It is designed for the ShopSphere single-node kind proof-of-concept and is **not production high availability**.

## Storage and network boundary

The StatefulSet requests an 80 Gi `ReadWriteOnce` volume from kind's `standard` local-path StorageClass. The retained PVC allows data to survive PostgreSQL pod restart and ordinary StatefulSet replacement. Data can still be lost if the PVC, kind node, kind cluster, VM disk, or VM is deleted or corrupted. A backup held only on the same VM is not disaster recovery.

The `postgresql` Service is explicitly `ClusterIP` and exposes port 5432 only inside Kubernetes. A NetworkPolicy declares ingress from the application and platform namespaces. NetworkPolicy enforcement depends on the cluster network plugin and must be verified for the installed kind networking configuration. There is no NodePort, LoadBalancer, host-port mapping, or public PostgreSQL firewall rule.

## Credentials

The committed `postgresql-secret.example.yaml` contains placeholders only and is not part of Kustomize. Do not edit it with real values. Generated `postgresql-secret.yaml` and `postgresql-secret.env` files are ignored, but creating secret files is discouraged.

Create the live Secret using hidden prompts:

```bash
make postgresql-secret
```

For controlled automation, explicitly request strong generated values:

```bash
./scripts/create-postgresql-secret.sh --generate
```

The helper writes directly to the Kubernetes API, does not print credentials, and preserves an existing Secret. Store production credentials in an approved external secret manager; a Kubernetes Secret is not a complete secret-management system.

## Validate, deploy, and verify

```bash
make validate-postgresql
make postgresql-apply
kubectl --context kind-shopsphere-poc -n shopsphere-data rollout status statefulset/postgresql --timeout=300s
make postgresql-status
```

The database names are `customer_db` and `keycloak_db`. Initialization runs only when PostgreSQL starts with an empty data directory. Changing the ConfigMap does not migrate an existing database.

## PoC backup

Create database-format backups without printing database credentials:

```bash
mkdir -p backups/postgresql
kubectl --context kind-shopsphere-poc -n shopsphere-data exec postgresql-0 -- \
  sh -ec 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname customer_db' \
  > backups/postgresql/customer_db.dump
kubectl --context kind-shopsphere-poc -n shopsphere-data exec postgresql-0 -- \
  sh -ec 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname keycloak_db' \
  > backups/postgresql/keycloak_db.dump
```

Restrict backup file permissions, encrypt copies, define retention, and transfer protected copies away from the VM. Verify backups with `pg_restore --list` and conduct periodic restoration rehearsals. Backup files may contain personal and identity configuration data even though they do not contain the live Kubernetes Secret.

## PoC restore

Restore is a data-changing maintenance operation. Stop dependent writers, take a fresh backup, verify the target database, and obtain explicit operator approval. A typical custom-format restore is:

```bash
kubectl --context kind-shopsphere-poc -n shopsphere-data exec -i postgresql-0 -- \
  sh -ec 'pg_restore --exit-on-error --clean --if-exists --no-owner --username "$POSTGRES_USER" --dbname customer_db' \
  < backups/postgresql/customer_db.dump
```

Use `keycloak_db` and its matching backup for Keycloak. Restoration does not recreate Kubernetes Secrets. Role/password rotation must be coordinated between PostgreSQL and the Secret; replacing only the Secret will break existing database authentication.

## Production evolution

Production should use managed PostgreSQL with regional or equivalent high availability, automated encrypted backups, point-in-time recovery (PITR), synchronous or service-appropriate replication, tested failover, deletion protection, private connectivity, a NetworkPolicy-capable cluster network, monitored capacity, managed credential rotation, and regularly exercised restoration and disaster-recovery procedures. The single PostgreSQL pod and node-local volume implemented here do not provide those guarantees.
