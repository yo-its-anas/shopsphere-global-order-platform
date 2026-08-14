# Kafka PoC Overlay

This overlay deploys the internal single-broker KRaft topology. It contains no credentials because the PoC listener is private plaintext and unauthenticated; access is constrained by Kubernetes service discovery and NetworkPolicy where the CNI enforces policy.

```bash
make validate-kafka
make kafka-apply
make kafka-topics
make kafka-status
```

After catalogue-service is deployed, `make catalogue-event-smoke` creates simulated catalogue/inventory changes through a temporary Keycloak service identity. The script never prints the generated client credential or access token and deletes the temporary client on exit. It intentionally leaves the simulated domain records and their evidence events in the PoC databases/topics.

The governed topics use a domain, fact, and contract-version convention:

- `catalogue.product.created.v1`
- `catalogue.product.updated.v1`
- `catalogue.price.changed.v1`
- `inventory.adjusted.v1`
- `inventory.low.v1`
- `inventory.out-of-stock.v1`
- `inventory.reserved.v1`
- `inventory.reservation_released.v1`
- `inventory.reservation_consumed.v1`

All topics have one partition and replication factor one in this PoC. This preserves per-topic append order but cannot provide cross-topic ordering or broker redundancy.
