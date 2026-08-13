# Catalogue and Inventory Administrator Guide

This guide covers the implemented `operations_admin` capability. Use simulated PoC data
only. Do not use bootstrap Keycloak administration credentials for application actions.

## Product and category governance

- `/categories` lists and creates categories. Slugs are normalized and unique; parent
  relationships cannot form cycles.
- `/products/new` registers a product with a unique normalized SKU. SKU is immutable
  through ordinary update operations.
- `/products/{productId}/edit` changes allowed metadata/lifecycle fields. Deactivation
  hides the product from customer search.
- `/products/{productId}/pricing` sets an immediately effective positive decimal price
  for a supported currency. The previous active price is closed and retained.

All writes travel through API Gateway. A `409` indicates a uniqueness/state/concurrency
conflict; `422` indicates input validation; `403` indicates insufficient role. Do not
bypass these controls with direct database updates.

## Inventory operations

Use `/inventory/{productId}/adjust` to initialize or adjust stock. Verify the product,
movement type, signed quantity, reason and confirmation before submission.

- `INITIAL_STOCK` establishes the first balance.
- `STOCK_RECEIPT` increases on-hand stock.
- `DAMAGE` decreases on-hand stock.
- `MANUAL_ADJUSTMENT` and `CORRECTION` require an auditable non-zero delta.

The service locks/version-checks the inventory row, rejects negative stock, and records
an append-only movement with actor, correlation ID and previous/resulting balances.
Availability is derived and must never be edited directly. Reservation/release/
fulfilment commands are not implemented.

## Operational evidence and events

Movement history is available at `/inventory/{productId}/movements`; calculated
statistics are at `/inventory/statistics`. PostgreSQL is authoritative for both.

Each accepted product, price or inventory transaction can append a versioned outbox
event in the same PostgreSQL transaction. A background relay publishes asynchronously
to Kafka and marks the row only after broker acknowledgement. Delivery is at least once;
future consumers must deduplicate by `event_id`. Kafka failure leaves a retryable outbox
row and must not trigger direct re-entry of the stock command.

Useful non-destructive checks are:

```bash
make postgresql-status
make redis-status
make kafka-status
make catalogue-service-status
make api-gateway-status
```

Never print Kubernetes Secret data, database URLs, Redis passwords, bearer tokens or
Keycloak client secrets. Redis is a cache only; clearing or losing it must produce cache
misses, not manual reconstruction of authoritative balances.

## Current evidence and limitations

Backend, frontend and platform checks passed at the boundaries documented in the
[evidence assessment](../evidence/catalogue-inventory-integration-evidence.md). The
explicitly enabled live integration suite passed all 11 scenarios, and the principal
administrator workflow was also validated manually through the authenticated UI.

The PoC has one PostgreSQL instance, one Redis instance, one Kafka broker/controller,
one kind node and one physical VM. It has no host-level high availability. Production
requires managed/HA PostgreSQL, replicated Redis, multi-broker Kafka, multiple nodes and
zones, autoscaling, external secret management and stronger enforced network/security
boundaries.
