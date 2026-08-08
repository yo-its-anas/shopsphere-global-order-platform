# PostgreSQL Base

Provides the reusable single-instance PostgreSQL StatefulSet, internal ClusterIP service, persistent volume claim, initialization script, resource controls, health probes, and ingress policy. It contains no Secret and is deployed only through an explicit environment overlay.

The initialization creates `customer_db` owned by `customer_app` and `keycloak_db` owned by `keycloak_app`. PostgreSQL authentication data remains in the separately managed `shopsphere-postgresql-credentials` Kubernetes Secret.
