# Catalogue and Inventory User Guide

The React application implements Product Catalogue and Inventory screens backed by API
Gateway routes. Frontend role checks control navigation only; catalogue-service remains
authoritative for JWT validation, RBAC and data visibility.

## Customer workflow

After Keycloak sign-in, a customer can:

1. Open `/products` to search, filter by category and page through active/searchable
   products.
2. Open `/products/{productId}` to view product details, current pricing and safe
   availability.
3. Read availability as the persisted on-hand quantity minus reserved quantity. The UI
   cannot edit availability and does not treat Redis as authoritative.

Customers cannot open administrative create/edit, category, pricing, operational
inventory, adjustment, movement or statistics routes. Hiding navigation is not the
security control: backend attempts return `403` where appropriate.

## Support workflow

A support user can read operational catalogue records and use:

- `/inventory` for tracked balances;
- `/inventory/{productId}/movements` for append-only movement history; and
- `/inventory/statistics` for calculated counts and unit totals.

Support remains read-only. It cannot register/update products, categories or prices and
cannot initialize or adjust stock.

## Operations administrator workflow

An `operations_admin` receives the support views plus governed routes for product,
category, pricing and inventory management. Stock changes require explicit confirmation,
a reason, an idempotency key and, for existing inventory, the observed version.
Instructions for these operations are in the
[administrator guide](catalogue-inventory-administration.md).

## States and errors

The implemented screens provide loading, empty, validation, unauthorized and API
unavailable states. API requests use `VITE_API_BASE_URL`, which must identify API Gateway;
the browser must not call catalogue-service directly. Tokens and secrets must never be
copied into screenshots, logs or issue reports.

## Evidence boundary

Six focused React catalogue/inventory tests passed, covering search/filtering, product
registration permission, category/price commands, inventory/movement/statistics
presentation, adjustment confirmation, API errors and unauthorized routes. The
production frontend build passed.

The explicitly enabled live catalogue integration report contains 11 passes with zero
skips, failures, or errors. The principal authenticated browser → Keycloak → API Gateway
→ catalogue-service product search/detail/price/availability journey also passed. The
inventory-statistics browser page remains **Pending / Not Verified** even though its
authenticated Gateway integration test passed.
