# Customer Service PoC Overlay

This opt-in overlay deploys customer-service into `shopsphere-apps`. It is not part of the root PoC overlay because deployment requires runtime Secrets and a ready PostgreSQL service.

## Runtime configuration

The generated ConfigMap contains only non-secret service identity, environment, structured-log level, database timeout, and Keycloak locations. The public issuer is kept separate from the internal JWKS, Admin API, and service-account token endpoints. This split is required because issuer validation must exactly match browser-issued tokens, while back-channel calls must use private Kubernetes service discovery.

The Deployment reads:

- `DATABASE_URL` from `shopsphere-customer-service-database/database-url`;
- the least-privilege Keycloak event-reader client identifier and credential from `shopsphere-customer-activity-keycloak`.

Create the database Secret directly through the Kubernetes API without printing the credential:

```bash
make customer-service-secret
```

The helper derives an encoded SQLAlchemy URL from the existing PostgreSQL Secret. It preserves an existing target Secret. The committed example is a placeholder only and is not rendered by Kustomize.

Validate and deploy:

```bash
make validate-customer-service
make customer-service-apply
make customer-service-status
```

The Service is ClusterIP-only and has no Ingress, NodePort, or LoadBalancer. API Gateway is the intended caller. NetworkPolicy enforcement requires a compatible CNI; the default kind networking setup must not be assumed to enforce it.

The single replica, single kind node, and single VM are a PoC availability limitation. Multiple replicas on that host would not provide host-level high availability.
