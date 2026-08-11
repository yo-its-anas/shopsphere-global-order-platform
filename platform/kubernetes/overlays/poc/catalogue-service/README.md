# Catalogue Service PoC Overlay

This overlay supplies environment-safe PostgreSQL, Keycloak, Redis, and Kafka endpoints. Runtime database and Redis passwords come from namespace-scoped Secrets and are never committed. Kafka has no client credential in the private PoC topology. Use the Makefile build/load/apply/status workflow after PostgreSQL, Keycloak, Redis, and Kafka are available.

The service is internal only. Redis outages degrade to PostgreSQL reads; Kafka outages retain committed outbox rows for retry; PostgreSQL outages make readiness fail. The single replica and single kind node provide no host-level high availability.
