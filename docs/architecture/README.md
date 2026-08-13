# Architecture

Separates the implemented PoC architecture from recommended production architecture so constraints and future-state decisions remain unambiguous.

## Capability designs

- [Product Catalogue and Inventory domain design](catalogue-inventory-domain-design.md) — implemented catalogue/inventory aggregates, invariants, authorization and concurrency, plus Planned Order Processing integration and PoC-to-production evolution.
- [Enterprise Order Processing domain design](order-processing-domain-design.md) — implemented customer-owned cart foundation plus the target immutable order snapshots, reservation Saga, idempotency, lifecycle, audit, security, and failure handling. Checkout and order lifecycle implementation remain Planned.
