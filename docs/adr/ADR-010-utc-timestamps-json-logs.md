# ADR-010: Use UTC for stored timestamps and structured JSON logs

## Status

Accepted — service JSON logging, UTC domain timestamps, and correlation IDs exist.
Consistent service/environment/trace fields, OpenTelemetry instrumentation, Loki
collection, log-schema enforcement, and centralized retention remain Planned.

## Context

ShopSphere represents global activity across services. Local timestamps and unstructured messages create ambiguity during ordering, analytics, troubleshooting, audit, and incident correlation.

## Decision

Store timestamps as timezone-aware UTC values and emit them in ISO 8601 format. Convert to user-local time only at presentation boundaries. Emit structured JSON application logs with UTC timestamp, severity, service, environment, event name, trace identifier, span identifier, and correlation identifier where available.

Keep operational logs, domain audit records, and identity-provider authentication events as distinct record classes. Customer-domain audit records are owned by `customer-service`; authentication events are owned by Keycloak. Cross-system customer activity views may present an authorized, minimal projection of both, but do not transfer source-of-truth ownership. Event correlation uses opaque correlation and trace identifiers, never credentials or bearer tokens.

Catalogue lifecycle and price changes record verified actor, correlation, and UTC effective/occurrence times. InventoryMovement is an immutable business fact with a UTC `occurred_at` instant and resulting balances; it is not an application log. Price validity uses UTC instants while currency and any future market/business-zone context remain explicit domain fields.

The target Order Processing context applies the same distinction: OrderStatusHistory and
OrderAuditEvent are append-only domain records, OrderOutboxEvent is publication intent,
and structured logs are operational telemetry. Order times, reservation expiry, Saga
state changes, and event occurrence use UTC; a customer's display timezone remains a
presentation concern.

## Alternatives considered

- Store local time: appears user-friendly but creates daylight-saving and cross-region ambiguity.
- Plain-text logs: readable locally but fragile for automated parsing and correlation.
- Store UTC plus every user's zone on each record: redundant for most domain records; retain business-relevant zone context separately only when required.

## Consequences

Events and logs can be correlated consistently across systems. Developers must use timezone-aware types and preserve separate business timezone fields when their meaning matters. JSON logs are less visually compact without tooling.

## Security implications

Logs must exclude credentials, tokens, payment data, and unnecessary personal data; apply redaction, access controls, integrity protection, retention, and deletion policy. Correlation identifiers must not encode sensitive values.

Audit records require stronger modification controls than ordinary application logs and must capture a verified actor, action, target, outcome, source, and UTC event time without copying sensitive before/after values unnecessarily. Authentication-event retention and presentation must account for the sensitivity of IP address, device, location, and failed-login metadata.

Inventory logs and movement reasons must not contain bearer tokens, credentials, customer personal data, or unrestricted operator text. Movement history needs append-only controls, access limits, retention governance, and correlation without treating a log stream as the stock ledger.

## PoC limitations

One-host clock behavior does not prove multi-region clock discipline. Application traces
and log trace correlation are implemented, but no OpenTelemetry Collector, trace backend,
Loki pipeline, or automated log-schema enforcement is deployed.

## Production evolution

Enforce synchronized clocks, centralized schema validation, protected and durable trace
and log storage, retention tiers, alerting, audit immutability where required, and
regional compliance controls.

The target log, trace, label, and Loki-index conventions are defined in
[ADR-012](ADR-012-layered-observability-source-owned-kpis.md) and the
[observability architecture](../architecture/observability-architecture.md).

## Viva defence notes

Explain the distinction between an instant and a business-local representation. UTC removes storage ambiguity; user timezone remains presentation or domain context. Structured logs support machine correlation and measurable operations.
