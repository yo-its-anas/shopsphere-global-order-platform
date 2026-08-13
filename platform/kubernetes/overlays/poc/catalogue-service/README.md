# Catalogue Service PoC Overlay

This overlay supplies environment-safe PostgreSQL, Keycloak, Redis, and Kafka endpoints. Runtime database and Redis passwords come from namespace-scoped Secrets and are never committed. Kafka has no client credential in the private PoC topology. Use the Makefile build/load/apply/status workflow after PostgreSQL, Keycloak, Redis, and Kafka are available.

The service is internal only. Redis outages degrade to PostgreSQL reads; Kafka outages retain committed outbox rows for retry; PostgreSQL outages make readiness fail. The single replica and single kind node provide no host-level high availability.

Runtime configuration uses `catalogue_db` through `shopsphere-catalogue-service-database`, Redis credentials through `shopsphere-catalogue-cache`, the internal Keycloak issuer/JWKS contract, and the internal Kafka bootstrap Service. The Service is ClusterIP-only and API Gateway is the intended application entry point. The NetworkPolicy allows gateway ingress and dependency-specific egress, but kindnet does not enforce NetworkPolicy; use a compatible CNI before treating it as isolation.

```bash
make validate-catalogue-service
make catalogue-service-build
make catalogue-service-load
make catalogue-service-apply
make catalogue-service-status
```
