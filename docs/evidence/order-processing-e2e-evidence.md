# Enterprise Order Processing End-to-End Evidence

Executed: `2026-08-13T20:08:36Z`
Synthetic data prefix: `order-e2e-0a16386d1d`

No password, token, client secret, or Kubernetes Secret value is retained.

The accompanying non-live validation review records 46 passing order-service tests,
33 passing focused API Gateway order-proxy tests, and 11 passing frontend order tests.
The live JUnit/JSON evidence contains 10 passed checks (prerequisites plus scenarios A–I),
zero failures and zero skips.

## Manual browser evidence

On 2026-08-14, the customer happy path was also manually exercised in Firefox through
the deployed React application and API Gateway. Customer quantity `2` of synthetic SKU
`ORDER-DEMO-HAPPY-001` produced confirmed order number
`SS-20260814-1EA297D4F967`. The customer navigated Catalogue → Product → Cart → Checkout
→ Confirmation → My Orders → Order Detail → Status Timeline. Authoritative available
inventory decreased by two through the reservation model. This is retained manual UI
evidence for the happy path only; it does not substitute for manual execution of the
separate stock-safety, price-change, IDOR, or duplicate-checkout demonstrations.

| Scenario | Result | Classification | Evidence |
| --- | --- | --- | --- |
| Prerequisites | **PASSED** | Platform Validated | Keycloak, PostgreSQL, customer, catalogue, order, Gateway, Redis and Kafka checks passed; three temporary identities authenticated. |
| A — Successful order | **PASSED** | End-to-End Validated | SS-20260813-C3E0A41976EA (c3e0a419-76ea-053d-027b-ad7188b83831) confirmed at USD 39.9800; reserved=2, available=8; 2 outbox rows observed. |
| B — Insufficient inventory | **PASSED** | End-to-End Validated | HTTP 409; no order, negative stock, or stranded ACTIVE reservation. |
| C — Price change | **PASSED** | End-to-End Validated | 2a29a301-7de0-01eb-29aa-af2b43161a31 used authoritative USD 12.5000, not stale USD 10.0000. |
| D — Idempotent retry | **PASSED** | End-to-End Validated | Both calls recovered 510ff615-e220-0d08-061a-e1e01d390a96; one order and one reservation. |
| E — IDOR | **PASSED** | End-to-End Validated | Arbitrary-cart Gateway path and Customer B order both returned 404 to Customer A. |
| F — Concurrent final unit | **PASSED** | End-to-End Validated | Concurrent results 201/409; winner=29d214d0-c04b-0211-3c1e-f33f67fe5d95; available=0, reserved=1. |
| G — Cancellation | **PASSED** | End-to-End Validated | b6a82ce2-c55e-05bf-0a7f-96be1fd91675 cancelled twice; one history transition and no ACTIVE reservation. |
| H — Kafka failure | **PASSED** | End-to-End Validated | e59707f7-5f51-0e8a-05d1-3efa80f01473 remained CONFIRMED; pending outbox published after Kafka restoration. |
| I — Redis failure | **PASSED** | End-to-End Validated | PostgreSQL fallback confirmed 28711ac9-2030-0dfb-3be2-c814df6f7ab9 at USD 9.0000; Redis restored. |

## Classification

Passed live scenarios are **End-to-End Validated** through API Gateway. Failed or skipped
scenarios are **Pending / Not Verified**; unit results are not substituted. The automated
run was API-driven and did not automate Firefox or another browser. The separate manual
record above validates the browser happy path without changing the scope of the automated
evidence.

## Examination requirement coverage

| Requirement | Direct evidence | Evidence status |
| --- | --- | --- |
| Create customer shopping carts | Scenario A added and retrieved a persisted cart; E denied an arbitrary cross-customer cart path | **End-to-End Validated** |
| Validate product availability | B rejected insufficient stock without a reservation; F allowed one final-unit winner; G released cancellation stock | **End-to-End Validated** |
| Process customer orders | A completed authenticated checkout; D proved one order/reservation across retry; H/I proved designed dependency behavior | **End-to-End Validated** |
| Generate order confirmations | A returned a unique order number/UUID and retrieved the committed detail | **End-to-End Validated** |
| Calculate order totals | A verified USD 39.9800; C used authoritative 12.5000 instead of stale 10.0000 | **End-to-End Validated** |
| Track order status | A read CONFIRMED history; G created exactly one CANCELLED history transition | **End-to-End Validated** |
| Maintain complete order history | A verified list, detail and non-empty status history; E verified order IDOR denial | **End-to-End Validated** |
| Produce transaction audit logs | A and G required non-empty safe audit responses; H proved recoverable outbox state | **End-to-End Validated** |

## PoC limitation

This tests one physical GCP VM, one kind node, logical databases on one PostgreSQL
server, one Redis pod and one Kafka broker. Customer, catalogue and order workloads share
that host. Inventory reservation and order creation remain separate transactions joined
by a Saga; outage recovery is not infrastructure-level high availability.
