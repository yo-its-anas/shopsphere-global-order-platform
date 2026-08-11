# Catalogue Service PoC Overlay

This overlay supplies environment-safe PostgreSQL, Keycloak, and Redis endpoints. Runtime database and Redis passwords come from namespace-scoped Secrets and are never committed. Use the Makefile build/load/apply/status workflow after PostgreSQL, Keycloak, and Redis are available.

The service is internal only. Redis outages degrade to PostgreSQL reads; PostgreSQL outages make readiness fail. The single replica and single kind node provide no host-level high availability.
