# Enterprise Order Processing End-to-End Validation

This explicitly enabled runner exercises the deployed PoC through API Gateway using
randomized simulated catalogue, inventory, customer, and order data. It creates three
temporary confidential Keycloak service-account clients: two carry only `customer`, and
one carries only `operations_admin`. Credentials and tokens stay in process memory and
are never written to reports or printed.

Run only against the controlled PoC cluster:

```bash
make order-e2e PYTHON=services/order-service/.venv/bin/python
```

The runner verifies all required workloads first, executes successful checkout,
insufficient inventory, authoritative price change, idempotent retry, IDOR, concurrent
final-unit, cancellation, Kafka outage/recovery, and Redis fallback scenarios. Kafka and
Redis are scaled to zero only during their bounded scenarios and restored in cleanup.
After any interrupted run, verify `make kafka-status` and `make redis-status`.

Evidence is written to:

- `test-results/end-to-end/order-processing.json`
- `test-results/end-to-end/order-processing.xml`
- `docs/evidence/order-processing-e2e-evidence.md`

The runner retains append-only synthetic orders, movements, audits, and outbox records as
evidence because the domain intentionally provides no destructive deletion APIs. Its
randomized `order-e2e-*` prefix distinguishes these records. Temporary Keycloak clients
are removed. Never run this against production.
