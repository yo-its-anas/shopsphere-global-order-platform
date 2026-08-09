# ShopSphere Enterprise Frontend

React, TypeScript, and Vite frontend for ShopSphere Global Enterprise Order Management. The executive dashboard retains clearly labelled development fixtures; Customer Identity and Account Management pages use authenticated API Gateway requests.

## Stitch design integration

Two static Stitch exports informed this frontend. The original operations dashboard established the application shell. The customer export at `/opt/shopsphere/stitch-customer-ui/stitch_shopsphere_enterprise_operations` added visual references for secure entry, registration, profile, addresses, account activity, and customer administration.

Preserved design elements include:

- the dark enterprise sidebar, fixed header, compact navigation, and environment context;
- white outlined surfaces, deep-blue primary actions, restrained status colors, and dense tables;
- profile summary and identity-provider management panels;
- address cards with default-address treatment and explicit actions;
- activity and administration table hierarchy;
- centered sign-in and registration cards.

The generated HTML was not copied directly. The following were discarded:

- repeated HTML document shells and per-page Tailwind CDN configuration;
- duplicate Google font and Material Symbols imports;
- remote profile images and generated brand-image placeholders;
- `href="#"` navigation and controls without behavior;
- hard-coded customer names, addresses, activity records, IP addresses, production labels, roles, and account statistics;
- local sign-in and registration forms that would incorrectly duplicate Keycloak credential ownership;
- the Stitch profile reference to Okta, because ShopSphere uses Keycloak;
- CSV export buttons because no reviewed export API currently exists.

No Stitch dependency or runtime is required.

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

Frontend role checks are presentation controls only. They determine navigation and route visibility but do not grant access. API Gateway and customer-service remain authoritative for authentication, role authorization, ownership, and IDOR prevention.

The Keycloak client must use exact environment-specific redirect URIs and web origins. Do not use wildcard production origins.

## Routes

| Route                                                                   | Access                                  | Data source                         |
| ----------------------------------------------------------------------- | --------------------------------------- | ----------------------------------- |
| `/login`                                                                | Public                                  | Keycloak redirect                   |
| `/register`                                                             | Public                                  | Keycloak self-registration redirect |
| `/dashboard`                                                            | Authenticated                           | Centralized dashboard mock data     |
| `/customers`                                                            | Authenticated                           | Role-aware landing redirect         |
| `/profile`                                                              | `customer` UX role                      | API Gateway customer profile API    |
| `/addresses`                                                            | `customer` UX role                      | API Gateway address APIs            |
| `/account-activity`                                                     | `customer` UX role                      | API Gateway normalized activity API |
| `/customer-administration`                                              | `support` or `operations_admin` UX role | API Gateway administration API      |
| `/products`, `/inventory`, `/orders`, `/platform-health`, `/audit-logs` | Authenticated                           | Existing honest placeholders        |
| `/unauthorized`                                                         | Authenticated                           | Local safe authorization state      |

Operations administrators can request explicit customer status changes. Support users receive a read-only administration view. The backend enforces the actual permissions in both cases.

## API integration boundary

`src/services/apiClient.ts` is the only generic HTTP boundary. `src/services/customerApi.ts` maps typed customer operations onto relative paths beneath `VITE_API_BASE_URL`. That base URL must identify API Gateway; frontend code contains no customer-service origin.

The client refreshes the access token immediately before an authenticated request and adds it to the `Authorization` header. Tokens are never placed in local storage, session storage, UI state, errors, or logs.

Profile loading performs a GET first. A genuine 404 triggers the idempotent profile-provisioning PUT; other errors remain errors. Customer pages provide loading, empty, validation/error, unauthorized, and API-unavailable presentations.

Dashboard values remain in `src/mocks/dashboard.ts` and retain the visible **Demo Data** indicator. Customer API data is not replaced with fixtures in the running application.

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

Tests cover application rendering, authenticated and unauthenticated routing, PKCE adapter initialization, role-aware navigation, profile rendering, address creation/deletion, unauthorized administration, and safe API-unavailable behavior.

## Container build

```bash
docker build -t shopsphere/frontend:foundation .
docker run --rm -p 8080:8080 shopsphere/frontend:foundation
```

The multi-stage image compiles static assets with Node and serves them through unprivileged Nginx as UID/GID 101 on port 8080. Runtime environment injection is not implemented. The Dockerfile accepts the four public `VITE_*` settings as build arguments; never use those arguments for secrets.
