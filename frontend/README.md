# ShopSphere Enterprise Frontend

React and TypeScript presentation foundation for the ShopSphere Global Enterprise Order Management Platform. This Day 1 frontend uses fictional development fixtures only. It is not authenticated and does not connect to live backend, identity, or telemetry services.

## Stitch design provenance

The source export at `/opt/shopsphere/stitch-export` contained a static `code.html`, `screen.png`, and `DESIGN.md`. The integrated frontend preserves its reusable visual language:

- dark enterprise sidebar and blue active navigation;
- global search/header bar and environment indicator;
- Executive Dashboard hierarchy and full-width alert treatment;
- KPI cards, recent-orders table, and platform-health meters;
- compact enterprise spacing, tonal surfaces, status colors, and technical monospace data.

The generated HTML itself was not copied. Its Tailwind CDN runtime, duplicate Google Material Symbols imports, temporary Google-hosted images, dead `href="#"` links, hard-coded production label, and hard-coded business figures were removed.

## Refactored architecture

```text
src/
├── app/          # application entry, routing, and global design tokens
├── components/   # reusable presentation and state components
├── config/       # validated environment-facing configuration boundary
├── features/     # feature-owned presentation components
├── layouts/      # enterprise application shell
├── mocks/        # centralized fictional development data
├── pages/        # route-level pages and placeholders
├── services/     # backend-neutral API client abstraction
├── test/         # shared test setup
└── types/        # shared TypeScript contracts
```

React Router currently provides `/login`, `/dashboard`, `/customers`, `/products`, `/inventory`, `/orders`, `/platform-health`, and `/audit-logs`. Login and business routes are honest placeholders; authentication and authorization are not implemented.

Loading, empty, and error presentations are reusable and ready for asynchronous integration. Dashboard mock values live only in `src/mocks/dashboard.ts` and are visibly marked **Demo Data** throughout the application.

## API integration boundary

Copy `.env.example` to an ignored `.env.local` when local configuration is needed:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

`src/services/apiClient.ts` owns the generic fetch and error abstraction. Future feature-specific clients should use it and map backend payloads into the interfaces in `src/types/`. No component currently invokes the client, and no real backend request is made.

Vite environment variables are public browser configuration. Never place credentials, tokens, private URLs, or other secrets in `VITE_*` values.

## Run locally

Requires Node.js 20.19 or later.

```bash
npm ci
npm run dev
```

The development server binds to `127.0.0.1:5173` by default.

## Quality and tests

```bash
npm run format:check
npm run lint
npm test
npm run build
```

Vitest and React Testing Library cover application rendering, the dashboard component, and routing. Tests exercise local mock presentation only.

### Dependency advisory note

As of 2026-08-07, `npm audit` reports the React Router RSC server-action advisory `GHSA-qwww-vcr4-c8h2` against `react-router-dom@7.18.2`. This frontend is a client-rendered static SPA and does not use React Server Components, server actions, SSR, route actions, or framework mode, so the affected execution path is absent. React Router 8.3.0 contains the upstream fix but requires Node 22.22+, while the current PoC host provides Node 20.20. This exception must be reassessed when the toolchain moves to Node 22; it is not a claim that application security is complete.

## Container build

```bash
docker build -t shopsphere/frontend:day1 .
docker run --rm -p 8080:8080 shopsphere/frontend:day1
```

The multi-stage build compiles static assets with Node and serves them through unprivileged Nginx as UID/GID 101 on port 8080. The Nginx configuration includes SPA route fallback and `/health`; runtime API configuration injection is not implemented yet.
