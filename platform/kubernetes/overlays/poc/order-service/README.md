# Order Service PoC Overlay

This overlay supplies non-secret PoC endpoints and tuning for the internal order-service.
Runtime database and Keycloak client credentials are created directly as Kubernetes
Secrets by the repository scripts and are never rendered by Kustomize or committed.

```bash
make order-service-secret
make order-service-identity
make validate-order-service
make order-service-build
make order-service-load
make order-service-apply
make order-service-status
```

The Service is ClusterIP-only. Browser and external API traffic normally enters through
API Gateway. PostgreSQL alone determines readiness; Catalogue and Keycloak failures are
reported by affected authenticated commands, and Kafka delivery recovers through the
transactional outbox.
