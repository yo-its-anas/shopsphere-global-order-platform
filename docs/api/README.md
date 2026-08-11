# ShopSphere API Documentation

FastAPI remains the executable OpenAPI source. Clients use API Gateway paths beneath `/api/v1`; the gateway forwards only registered method/path combinations to the internal ClusterIP-only customer-service and catalogue-service. The gateway propagates bearer tokens but does not currently validate them. Each downstream service remains authoritative for JWT validation, role enforcement, visibility, ownership, and domain invariants.

Interactive OpenAPI is available from a locally reachable service at `/docs`; the machine-readable document is `/openapi.json`. Do not expose the internal customer-service documentation endpoint publicly.

## Authentication and errors

Protected operations require `Authorization: Bearer <access-token>` issued by the `shopsphere` Keycloak realm for the `shopsphere-api` audience. Never place tokens in URLs, examples, screenshots, logs, or committed files.

Customer-service validates RS256 signature, issuer, audience, expiry, subject, and allow-listed roles. Expected responses include `400` for an invalid domain operation, `401` for missing or invalid authentication, `403` for insufficient role, `404` for an absent or non-owned resource, `409` for a uniqueness/state conflict, `422` for input validation, and safe `500`/`503` dependency failures. Gateway transport errors use `502`, `503`, and `504` without revealing the upstream origin.

## Customer self-service

All paths shown are both external gateway and internal service paths. Self-service ownership is resolved from the validated Keycloak `sub`; callers cannot select another customer profile ID.

| Method | Path | Role | Behavior |
| --- | --- | --- | --- |
| `PUT` | `/api/v1/customers/me` | `customer` | Idempotently provision or reuse the profile from verified identity claims. |
| `POST` | `/api/v1/customers/me` | `customer` | Explicitly create the current profile from validated profile input. |
| `GET` | `/api/v1/customers/me` | `customer` | Retrieve the caller's profile. |
| `PATCH` | `/api/v1/customers/me` | `customer` | Update allowed name, email, and phone fields. |
| `POST` | `/api/v1/customers/me/addresses` | `customer` | Create an owned address. |
| `GET` | `/api/v1/customers/me/addresses` | `customer` | List owned addresses. |
| `PATCH` | `/api/v1/customers/me/addresses/{address_id}` | `customer` | Update an owned address. |
| `DELETE` | `/api/v1/customers/me/addresses/{address_id}` | `customer` | Delete an owned address. |
| `PUT` | `/api/v1/customers/me/addresses/{address_id}/default` | `customer` | Select the default owned address. |
| `GET` | `/api/v1/customers/me/audit-history?offset=0&limit=50` | `customer` | Read customer-domain audit history. |
| `GET` | `/api/v1/customers/me/activity?offset=0&limit=50` | `customer` | Read normalized domain and Keycloak activity. |

Profile responses expose a domain UUID, allowed customer fields, account status, and UTC timestamps. They do not expose the Keycloak subject. Address input requires a two-letter ASCII country code and validates field lengths, postal characters, and international-style phone values.

## Support and operations administration

| Method | Path | Role | Behavior |
| --- | --- | --- | --- |
| `GET` | `/api/v1/admin/customers?offset=0&limit=50` | `support`, `operations_admin` | List profiles. |
| `GET` | `/api/v1/admin/customers/{customer_id}` | `support`, `operations_admin` | Retrieve one profile. |
| `GET` | `/api/v1/admin/customers/{customer_id}/audit-history` | `support`, `operations_admin` | Read domain audit history. |
| `GET` | `/api/v1/admin/customers/{customer_id}/activity` | `support`, `operations_admin` | Read normalized activity. |
| `PATCH` | `/api/v1/admin/customers/{customer_id}/status` | `operations_admin` | Apply an explicitly allowed status and reason code. |

Support is read-only. Frontend role visibility is a usability control only and cannot grant these API permissions.

## Activity model

Normalized activity returns `timestamp`, `event_category`, `action`, `source`, `result`, and allow-listed `context`. It excludes passwords, tokens, session identifiers, Keycloak secrets, raw event details, IP addresses, and administrator credentials. `/audit-history` is the customer-domain record; `/activity` combines that record with selected Keycloak events without copying raw Keycloak payloads into customer tables.

## Operational endpoints

- `GET /health/live` is dependency-free.
- `GET /health/ready` checks database connectivity and returns `503` when unavailable.
- `GET /api/v1/info` returns non-sensitive service metadata.

## Product Catalogue service

Catalogue-service implements `/api/v1` category, product, search, lifecycle, effective-pricing, inventory, availability, movement, and statistics routes. The API Gateway registers the exact same external method/path combinations and forwards them to its fixed `CATALOGUE_SERVICE_URL`; arbitrary catalogue subpaths are not proxied.

| Method | Path | Roles | Behavior |
| --- | --- | --- | --- |
| `POST` | `/api/v1/categories` | `operations_admin` | Create a normalized unique category. |
| `GET` | `/api/v1/categories[?active=...]` | All governed roles | List role-visible categories with pagination. |
| `GET` | `/api/v1/categories/{category_id}` | All governed roles | Retrieve a role-visible category. |
| `PATCH` | `/api/v1/categories/{category_id}` | `operations_admin` | Update allowed category fields and safe parent relationship. |
| `POST` | `/api/v1/products` | `operations_admin` | Register a product with immutable normalized SKU. |
| `GET` | `/api/v1/products` | All governed roles | Search/filter/sort/paginate products with customer visibility enforcement. |
| `GET` | `/api/v1/products/{product_id}` | All governed roles | Retrieve a role-visible product. |
| `PATCH` | `/api/v1/products/{product_id}` | `operations_admin` | Update explicitly allowed product fields. |
| `POST` | `/api/v1/products/{product_id}/deactivate` | `operations_admin` | Make a product inactive and non-searchable. |
| `GET` | `/api/v1/products/{product_id}/prices` | All governed roles | Retrieve current pricing; history is operational-role-only. |
| `PUT` | `/api/v1/products/{product_id}/prices/{currency_code}` | `operations_admin` | Close the prior price and create an immediately effective decimal price. |
| `GET` | `/api/v1/inventory/products/{product_id}/availability` | All governed roles | Return derived availability; customers receive no operational balance fields. |
| `GET` | `/api/v1/inventory/products/{product_id}` | `support`, `operations_admin` | Return operational on-hand, reserved, available, threshold, and version values. |
| `POST` | `/api/v1/inventory/products/{product_id}/initialize` | `operations_admin` | Establish tracked stock and its `INITIAL_STOCK` movement idempotently. |
| `POST` | `/api/v1/inventory/products/{product_id}/adjustments` | `operations_admin` | Apply a locked/versioned stock delta and append movement evidence. |
| `PATCH` | `/api/v1/inventory/products/{product_id}/settings` | `operations_admin` | Change the reorder threshold with an optional version guard. |
| `GET` | `/api/v1/inventory/products/{product_id}/movements` | `support`, `operations_admin` | Page through append-only movement history. |
| `GET` | `/api/v1/inventory[?state=...]` | `support`, `operations_admin` | List tracked balances and filter by derived availability state. |
| `GET` | `/api/v1/inventory/statistics` | `support`, `operations_admin` | Calculate stock counts and unit totals from persisted balances. |

Catalogue-service independently validates the same Keycloak issuer/audience/role assumptions as customer-service. Customers see active/searchable products, current prices, and safe derived availability only; support is read-only; operations administrators own mutations. API responses contain domain schemas rather than SQLAlchemy records. Inventory reservation/release/fulfilment commands remain unavailable until Order Processing integration is implemented.

## Evidence boundary

Catalogue route implementations, OpenAPI metadata, fixed Gateway mappings, schemas and
automated tests exist. The catalogue-service suite passed 48 tests; the focused React
catalogue/inventory suite passed 6 tests; Gateway proxy tests cover the allow-listed
transport. Current platform checks observed Ready internal Gateway and catalogue-service
workloads, and an unauthenticated live route reached backend JWT enforcement.

The catalogue integration report contains **11 skipped tests**. It does not prove an
authenticated browser or API workflow and must not be reported as passed. Accordingly,
the routes above are **Implemented**, **Unit Validated**, and platform-deployed at the
stated boundaries, but are **Pending / Not Verified** end to end.

PostgreSQL is authoritative for catalogue, pricing and inventory data. Redis caches
bounded read responses only and may be unavailable without invalidating PostgreSQL.
Kafka carries asynchronous versioned facts produced through the transactional outbox;
it is not part of the synchronous commit decision.
