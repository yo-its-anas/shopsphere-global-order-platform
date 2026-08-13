# Enterprise Order Processing End-to-End Evidence

Executed: `2026-08-13T20:08:36Z`
Synthetic data prefix: `order-e2e-0a16386d1d`

No password, token, client secret, or Kubernetes Secret value is retained.

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

Passed live scenarios are **End-to-End Validated** through API Gateway. Failed or skipped scenarios are **Not Verified**; unit results are not substituted.

## PoC limitation

This tests one VM, one kind node, one PostgreSQL instance, one Redis pod, and one Kafka broker. Outage recovery is not high availability.
