# PostgreSQL Base

Provides the reusable single-instance PostgreSQL StatefulSet, internal ClusterIP service, persistent volume claim, initialization script, resource controls, health probes, and ingress policy. It contains no Secret and is deployed only through an explicit environment overlay.

The idempotent initialization creates `customer_db` owned by `customer_app`, `keycloak_db` owned by `keycloak_app`, `catalogue_db` owned by `catalogue_app`, and `order_db` owned by `order_app`. PostgreSQL authentication data remains in the separately managed `shopsphere-postgresql-credentials` Kubernetes Secret.

PostgreSQL entrypoint initialization runs automatically only for an empty data directory. The repository reconciliation helper safely executes the same create-if-absent logic against an existing retained volume; it does not drop or recreate existing roles or databases.
