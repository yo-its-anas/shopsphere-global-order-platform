# Architecture

Separates the implemented PoC architecture from recommended production architecture so constraints and future-state decisions remain unambiguous.

## Capability designs

- [Product Catalogue and Inventory domain design](catalogue-inventory-domain-design.md) — implemented catalogue/inventory aggregates, invariants, authorization, concurrency and Order reservation integration, plus PoC-to-production evolution.
- [Enterprise Order Processing domain design](order-processing-domain-design.md) — implemented customer-owned carts, immutable order snapshots, reservation Saga, idempotency, lifecycle, audit, events, security and failure handling with explicit evidence boundaries.
