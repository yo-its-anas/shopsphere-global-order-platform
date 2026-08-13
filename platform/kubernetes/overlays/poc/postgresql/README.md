# PostgreSQL PoC Persistence

This overlay deploys one PostgreSQL 16 instance into `shopsphere-data` for Customer,
Keycloak, Product Catalogue/Inventory, and Order Processing logical databases. It is
designed for the ShopSphere single-node kind proof-of-concept and is **not production
high availability**.

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

The helper writes directly to the Kubernetes API and does not print credentials. For an
existing Secret, it adds only missing `catalogue-password` or `order-password` keys and
preserves every existing credential. Repeated execution preserves all existing values.

Derive the future catalogue-service runtime database URL into a separate namespace-local Secret:

```bash
make catalogue-service-secret
```

This helper creates `shopsphere-catalogue-service-database` in `shopsphere-apps`, preserves it on repeated execution, and never prints the URL or password. It does not deploy catalogue-service. Store production credentials in an approved external secret manager; a Kubernetes Secret is not a complete secret-management system.

Derive the future order-service runtime database URL into its own namespace-local Secret:

```bash
make order-service-secret
```

This creates `shopsphere-order-service-database` in `shopsphere-apps` and preserves it on
repeated execution. It does not deploy order-service or implement order behavior.

## Validate, deploy, and verify

```bash
make validate-postgresql
make postgresql-apply
kubectl --context kind-shopsphere-poc -n shopsphere-data rollout status statefulset/postgresql --timeout=300s
make postgresql-status
```

The required databases and owners are:

| Database | Owner | Capability |
| --- | --- | --- |
| `customer_db` | `customer_app` | Customer business data |
| `keycloak_db` | `keycloak_app` | Keycloak identity data |
| `catalogue_db` | `catalogue_app` | Product Catalogue and Inventory data |
| `order_db` | `order_app` | Enterprise Order Processing data |

Initialization runs automatically only when PostgreSQL starts with an empty data
directory. `make postgresql-apply` waits for the existing StatefulSet and then runs the
idempotent reconciliation helper, which creates only missing roles/databases and
reapplies restricted connect grants. It does not drop or recreate any database and does
not modify customer, Keycloak, or Catalogue schemas. `make postgresql-reconcile` can
safely repeat that reconciliation without applying manifests.

These logical databases and distinct owners reduce accidental cross-capability access, but they share one PostgreSQL process, persistent volume, kind node, and physical VM. This PoC resource optimization does not provide infrastructure-level isolation, independent scaling, or high availability.

## PoC backup

Create database-format backups without printing database credentials:

```bash
umask 077
mkdir -p backups/postgresql
kubectl --context kind-shopsphere-poc -n shopsphere-data exec postgresql-0 -- \
  sh -ec 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname customer_db' \
  > backups/postgresql/customer_db.dump
kubectl --context kind-shopsphere-poc -n shopsphere-data exec postgresql-0 -- \
  sh -ec 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname keycloak_db' \
  > backups/postgresql/keycloak_db.dump
kubectl --context kind-shopsphere-poc -n shopsphere-data exec postgresql-0 -- \
  sh -ec 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname catalogue_db' \
  > backups/postgresql/catalogue_db.dump
kubectl --context kind-shopsphere-poc -n shopsphere-data exec postgresql-0 -- \
  sh -ec 'pg_dump --format=custom --username "$POSTGRES_USER" --dbname order_db' \
  > backups/postgresql/order_db.dump
```

Restrict backup file permissions, encrypt copies, define retention, and transfer protected copies away from the VM. Verify backups with `pg_restore --list` and conduct periodic restoration rehearsals. Backup files may contain personal and identity configuration data even though they do not contain the live Kubernetes Secret.

## PoC restore

Restore is a data-changing maintenance operation. Stop dependent writers, take a fresh backup, verify the target database, and obtain explicit operator approval. A typical custom-format restore is:

```bash
kubectl --context kind-shopsphere-poc -n shopsphere-data exec -i postgresql-0 -- \
  sh -ec 'pg_restore --exit-on-error --clean --if-exists --no-owner --role=customer_app --username "$POSTGRES_USER" --dbname customer_db' \
  < backups/postgresql/customer_db.dump
```

Use `keycloak_db` with `--role=keycloak_app`, `catalogue_db` with
`--role=catalogue_app`, or `order_db` with `--role=order_app`, and the matching backup
for those capabilities. Always verify the selected target, owner role, and backup belong
together before approval. Restoration does not recreate Kubernetes Secrets.
Role/password rotation must be coordinated between PostgreSQL and the Secret; replacing
only the Secret will break existing database authentication.

## Production evolution

Production should use managed PostgreSQL with regional or equivalent high availability, automated encrypted backups, point-in-time recovery (PITR), synchronous or service-appropriate replication, tested failover, deletion protection, private connectivity, a NetworkPolicy-capable cluster network, monitored capacity, managed credential rotation, and regularly exercised restoration and disaster-recovery procedures. The single PostgreSQL pod and node-local volume implemented here do not provide those guarantees.

If Catalogue and Inventory develop different write contention, retention, availability, search, or scaling characteristics, place their data in independently managed databases or storage services with separate capacity, backup, recovery, access, and service-level objectives. Preserve API/event ownership and avoid cross-database writes or distributed transactions. Inventory balances and movement history require authoritative transactional storage; catalogue search and statistics may use separately scalable disposable projections.

Order workloads may develop different transaction volume, history retention, audit,
availability, and recovery requirements. Production should therefore permit Order data
to move to an independently managed and scaled HA PostgreSQL service without crossing
Catalogue ownership boundaries. Logical databases in this PoC are a resource
optimization, not fault isolation.
