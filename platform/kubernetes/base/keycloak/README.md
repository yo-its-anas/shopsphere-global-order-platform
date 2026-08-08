# Keycloak Base

Provides the reusable single-replica Keycloak deployment, internal ClusterIP service, ingress-policy intent, health probes, resource controls, and sanitized `shopsphere` realm import. The base contains no credentials and is deployed only through an explicit environment overlay.

The realm JSON uses Keycloak's native environment-variable placeholder resolution for frontend redirect and origin values. It creates no users and contains no passwords or client secrets. Version-controlled client-policy documents provide explicit S256 PKCE enforcement and are reconciled idempotently after startup import.
