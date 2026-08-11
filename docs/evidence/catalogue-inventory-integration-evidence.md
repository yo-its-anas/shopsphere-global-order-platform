# Product Catalogue and Inventory Integration Evidence

## Evidence scope

This report separates implementation presence from each validation layer. A test that
requires live services, credentials, cluster access, or an authorized outage is never
reported as passed when it was skipped or not executed.

| Capability | Implemented | Unit validated | Service-integration validated | Platform validated | Gateway/end-to-end validated | Current evidence |
|---|---|---|---|---|---|---|
| Categories and products | Yes | Yes | Pending/not executed | Not applicable | Pending/not executed | Catalogue API, repositories, migration, and unit tests exist; live suite added |
| Search, filters, pagination | Yes | Yes | Pending/not executed | Not applicable | Pending/not executed | PostgreSQL-backed query tests exist; live gateway assertions added |
| Pricing and currency validation | Yes | Yes | Pending/not executed | Not applicable | Pending/not executed | Decimal pricing API and unit tests exist; live assertions added |
| Inventory adjustments and availability | Yes | Yes | Pending/not executed | Not applicable | Pending/not executed | Inventory API/domain tests exist; live stock-flow assertions added |
| Movement history and statistics | Yes | Yes | Pending/not executed | Not applicable | Pending/not executed | Persisted query tests exist; live history/statistics assertions added |
| JWT and role enforcement | Yes | Yes | Pending/not executed | Keycloak configuration exists | Pending/not executed | Missing, invalid, expired, customer, support, and administrator cases added |
| Redis cache-aside and invalidation | Yes | Yes | Pending/not executed | Pending/not executed | Pending/not executed | API invalidation plus opt-in cache log and outage checks added |
| Kafka transactional outbox | Yes | Yes | Pending/not executed | Pending/not executed | Not applicable | Safe outbox publication and separately authorized recovery checks added |
| API Gateway catalogue routes | Yes | Yes | Not applicable | Gateway deployment exists | Pending/not executed | Suite requires the gateway URL or reports this layer as skipped |

## Automated artefacts

- Suite: `tests/integration/catalogue_inventory`
- Environment contract: `tests/integration/catalogue-inventory.env.example`
- Local/Jenkins command: `make catalogue-integration`
- Safe collection command: `make catalogue-integration-collect`
- JUnit report: `test-results/integration/catalogue-inventory.xml`

## Execution record

Repository validation performed while introducing this suite is recorded below. Live
service, platform, and gateway rows remain **Pending/not executed** until the opt-in
environment contract is supplied and the generated JUnit report shows the result.

- Test collection: **Validated**; 11 live integration tests collected successfully.
- Catalogue-service unit suite: **Validated**; 48 tests passed with 80% aggregate
  statement coverage.
- Disabled-by-default execution: **Validated**; JUnit XML was generated with 11 tests
  explicitly reported as skipped because live opt-in was absent. No skip was converted
  into a pass.
- Read-only PoC topology check: **Validated**; API Gateway, catalogue-service, Redis,
  and Kafka each reported one ready instance. Both application Services inspected were
  `ClusterIP`. This confirms availability of the platform targets, not passage of the
  credentialed integration scenarios.
- Live service integration: Pending/not executed; protected test credentials are not
  stored in the repository.
- Redis outage: Pending/not executed; explicit outage authorization not provided.
- Kafka outage/recovery: Pending/not executed; explicit outage authorization not
  provided.
