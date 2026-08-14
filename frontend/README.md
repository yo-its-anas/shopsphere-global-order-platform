# ShopSphere Enterprise Frontend

React, TypeScript, and Vite frontend for ShopSphere Global Enterprise Order Management. The executive dashboard retains clearly labelled development fixtures; Customer Identity, Product Catalogue/Inventory, and Enterprise Order Processing capabilities use authenticated API Gateway requests.

## Enterprise UI architecture

The shared visual system includes:

- the dark enterprise sidebar, fixed header, compact navigation, and environment context;
- white outlined surfaces, deep-blue primary actions, restrained status colors, and dense tables;
- profile summary and identity-provider management panels;
- address cards with default-address treatment and explicit actions;
- activity and administration table hierarchy;
- catalogue search/filter toolbars, product detail surfaces, and governed forms;
- inventory balance and movement tables, status indicators, adjustment confirmation, and statistic cards;
- cart, checkout review, immutable confirmation, order history/timeline, and governed order-management surfaces;
- centered sign-in and registration cards.

Presentation is implemented as React components using repository-owned CSS tokens. There is no runtime CSS CDN, remote icon library, duplicated page shell, placeholder navigation, or hard-coded business data. Unsupported delivery-address selection, shipping, payment, invoice, customer-contact, internal-notes, warehouse, supplier, transfer, and product-media controls are not presented as functional capabilities.

## Authentication architecture

The official `keycloak-js` adapter provides centralized authentication state in `src/features/auth`. It is configured for:

- OpenID Connect Authorization Code Flow (`standard`);
- S256 PKCE;
- a public frontend client with no client secret;
- redirect-based login, self-registration, and logout;
- in-memory tokens only;
- proactive token refresh and expired-session clearing;
- adapter role APIs rather than application-written JWT decoding;
- disabled adapter logging so tokens are not written to the console.

Frontend role checks are presentation controls only. They determine navigation and route visibility but do not grant access. API Gateway and downstream services remain authoritative for authentication, role authorization, ownership, visibility, and domain invariants.

The Keycloak client must use exact environment-specific redirect URIs and web origins. Do not use wildcard production origins.

## Routes

| Route                                        | Access                                  | Data source                                     |
| -------------------------------------------- | --------------------------------------- | ----------------------------------------------- |
| `/login`                                     | Public                                  | Keycloak redirect                               |
| `/register`                                  | Public                                  | Keycloak self-registration redirect             |
| `/dashboard`                                 | Authenticated                           | Centralized dashboard mock data                 |
| `/customers`                                 | Authenticated                           | Role-aware landing redirect                     |
| `/profile`                                   | `customer` UX role                      | API Gateway customer profile API                |
| `/addresses`                                 | `customer` UX role                      | API Gateway address APIs                        |
| `/account-activity`                          | `customer` UX role                      | API Gateway normalized activity API             |
| `/customer-administration`                   | `support` or `operations_admin` UX role | API Gateway administration API                  |
| `/products`                                  | customer, support, operations UX roles  | API Gateway catalogue search/read API           |
| `/products/:productId`                       | customer, support, operations UX roles  | API Gateway product, pricing, availability APIs |
| `/products/new`, `/products/:productId/edit` | `operations_admin` UX role              | API Gateway product commands                    |
| `/categories`                                | support or `operations_admin` UX role   | API Gateway category API                        |
| `/pricing`                                   | customer, support, operations UX roles  | API Gateway pricing API                         |
| `/inventory`                                 | support or `operations_admin` UX role   | API Gateway operational inventory API           |
| `/inventory/:productId/adjust`               | `operations_admin` UX role              | API Gateway inventory commands                  |
| `/inventory/:productId/movements`            | support or `operations_admin` UX role   | API Gateway movement API                        |
| `/inventory/statistics`                      | support or `operations_admin` UX role   | API Gateway persisted statistics API            |
| `/cart`, `/checkout`                         | `customer` UX role                      | API Gateway cart and checkout APIs              |
| `/orders`, `/orders/:orderId`                | `customer` UX role                      | API Gateway own-order and history APIs          |
| `/orders/confirmation/:orderId`              | `customer` UX role                      | Committed Gateway order confirmation            |
| `/order-management[/:orderId]`               | support or `operations_admin` UX role   | API Gateway operational order APIs              |
| `/platform-health`, `/audit-logs`            | Authenticated                           | Existing honest placeholders                    |
| `/unauthorized`                              | Authenticated                           | Local safe authorization state                  |

Operations administrators can request explicit customer status changes. Support users receive a read-only administration view. The backend enforces the actual permissions in both cases.

## API integration boundary

`src/services/apiClient.ts` is the only generic HTTP boundary. `src/services/customerApi.ts`, `src/services/catalogueApi.ts`, and `src/services/orderApi.ts` map typed capability operations onto relative paths beneath `VITE_API_BASE_URL`. That base URL must identify API Gateway; frontend code contains no direct microservice origin.

The client refreshes the access token immediately before an authenticated request and adds it to the `Authorization` header. Tokens are never placed in local storage, session storage, UI state, errors, or logs.

Profile loading performs a GET first. A genuine 404 triggers the idempotent profile-provisioning PUT; other errors remain errors. Catalogue pages load real products, categories, prices, availability, operational inventory, movements, and calculated statistics through gateway routes. Stock mutation requires explicit confirmation and sends a unique idempotency key plus the current inventory version. Pages provide loading, empty, validation/error, unauthorized, and API-unavailable presentations.

Order pages load the authenticated customer's cart, send cart mutations, and display only
preliminary estimates. Checkout sends no browser-authored prices or totals. A deliberate
checkout attempt receives an opaque client-generated idempotency key scoped to the cart ID
and version. The key is held in session storage solely for retry recovery, reused after an
unknown timeout outcome, and cleared after successful checkout or cart mutation. Tokens
remain in the Keycloak adapter's in-memory state and are never stored with the attempt.
Confirmation and detail screens render server-returned immutable commercial snapshots.
Support has operational read presentation; only operations administrators see lifecycle
command controls.

Dashboard values remain in `src/mocks/dashboard.ts` and retain the visible **Demo Data** indicator. Customer and catalogue/inventory API data are not replaced with fixtures in the running application.

## Configuration

Copy `.env.example` to an ignored `.env.local` when local configuration is required:

```dotenv
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_KEYCLOAK_URL=http://localhost:8081
VITE_KEYCLOAK_REALM=shopsphere
VITE_KEYCLOAK_CLIENT_ID=shopsphere-frontend
```

The Keycloak URL example assumes a protected local tunnel or port-forward. Vite variables are public browser configuration. Never place client secrets, passwords, service credentials, private backend addresses, JWTs, or refresh tokens in `VITE_*` values.

## Development and verification

Requires Node.js 20.19 or later.

```bash
npm ci
npm run dev
npm run lint
npm test
npm run build
```

Tests cover application rendering, authenticated and unauthenticated routing, PKCE adapter initialization, role-aware navigation, profile rendering, address creation/deletion, product rendering/search/filtering, customer write restrictions, product/category/price commands, inventory display/adjustment confirmation, movement history, statistics, cart empty/update/remove behavior, checkout and confirmation, idempotency-key preservation, stock/price conflicts, order list/detail/timeline, read-only support behavior, unauthorized order management, and safe API-unavailable behavior.

The frontend suite currently records 28 passing tests, and the production build passes.
These tests validate presentation, routing and API-adapter behavior with controlled
responses; they are not a live browser journey. Order UI is **Implemented** and **Unit
Validated**, while live browser End-to-End validation remains **Pending / Not Verified**.

## Container build

```bash
docker build -t shopsphere/frontend:foundation .
docker run --rm -p 8080:8080 shopsphere/frontend:foundation
```

The multi-stage image compiles static assets with Node and serves them through unprivileged Nginx as UID/GID 101 on port 8080. Runtime environment injection is not implemented. The Dockerfile accepts the four public `VITE_*` settings as build arguments; never use those arguments for secrets.
