"""Executive dashboard aggregation, resilience, and authorization tests."""

from app.domain.models import DependencyState
from app.infrastructure.service_clients import InvalidSourceResponseError, SourceTimeoutError
from tests.support import ApiClient, FakeSources

OPS = {"Authorization": "Bearer operations-token", "X-Request-ID": "dashboard-test"}
SUPPORT = {"Authorization": "Bearer support-token"}
CUSTOMER = {"Authorization": "Bearer customer-token"}


def test_complete_executive_summary_uses_real_source_aggregates(
    dashboard_client: ApiClient, sources: FakeSources
) -> None:
    response = dashboard_client.get("/api/v1/dashboard/summary", headers=OPS)

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["data_status"] == "complete"
    assert body["total_orders"] == 10
    assert body["total_revenue_simulated"] == "750.0000"
    assert body["revenue_currency"] == "USD"
    assert body["customer_count"] == 8
    assert body["product_count"] == 12
    assert body["available_product_count"] == 9
    assert body["low_stock_count"] == 3
    assert body["out_of_stock_count"] == 1
    assert body["fulfilled_orders"] == 3
    assert body["processing_orders"] == 2
    assert body["cancelled_orders"] == 2
    assert body["fulfilment_rate"] == "37.50"
    assert "payment settlement is not implemented" in body["revenue_label"]
    assert sources.tokens == ["operations-token"] * 3


def test_order_endpoint_exposes_simulated_revenue_rule(
    dashboard_client: ApiClient,
) -> None:
    response = dashboard_client.get("/api/v1/dashboard/orders", headers=OPS)

    assert response.status_code == 200
    body = response.json()
    assert body["revenue_included_statuses"] == ["CONFIRMED", "PROCESSING", "FULFILLED"]
    assert body["cancelled_orders"] == 2
    assert body["total_revenue_simulated"] == "750.0000"


def test_inventory_and_customer_counts_are_source_owned(
    dashboard_client: ApiClient,
) -> None:
    inventory = dashboard_client.get("/api/v1/dashboard/inventory", headers=SUPPORT)
    customers = dashboard_client.get("/api/v1/dashboard/customers", headers=SUPPORT)

    assert inventory.status_code == 200
    assert inventory.json()["available_product_count"] == 9
    assert inventory.json()["available_units"] == 100
    assert customers.status_code == 200
    assert customers.json()["customer_count"] == 8
    assert "business profiles" in customers.json()["customer_count_definition"]


def test_summary_is_partial_and_does_not_fabricate_failed_customer_zero(
    dashboard_client: ApiClient, sources: FakeSources
) -> None:
    sources.customer_error = SourceTimeoutError()

    response = dashboard_client.get("/api/v1/dashboard/summary", headers=OPS)

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["data_status"] == "partial"
    assert body["customer_count"] is None
    assert body["total_orders"] == 10
    assert body["product_count"] == 12
    assert {item["service"]: item["status"] for item in body["metadata"]["dependency_status"]}[
        "customer-service"
    ] == "timeout"


def test_single_dependency_timeout_returns_unavailable_with_null_values(
    dashboard_client: ApiClient, sources: FakeSources
) -> None:
    sources.order_error = SourceTimeoutError()

    response = dashboard_client.get("/api/v1/dashboard/orders", headers=OPS)

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["data_status"] == "unavailable"
    assert body["total_orders"] is None
    assert body["total_revenue_simulated"] is None
    assert body["cancelled_orders"] is None


def test_invalid_upstream_response_is_safe_and_not_zero(
    dashboard_client: ApiClient, sources: FakeSources
) -> None:
    sources.inventory_error = InvalidSourceResponseError("internal response detail")

    response = dashboard_client.get("/api/v1/dashboard/inventory", headers=SUPPORT)

    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["data_status"] == "unavailable"
    assert body["product_count"] is None
    assert body["available_units"] is None
    assert "internal response detail" not in response.text


def test_operations_health_and_alerts_use_actual_dependency_states(
    dashboard_client: ApiClient, sources: FakeSources
) -> None:
    sources.health_values[2] = sources.health_values[2].__class__(
        "order-service", None, DependencyState.UNAVAILABLE
    )

    operations = dashboard_client.get("/api/v1/dashboard/operations", headers=SUPPORT)
    alerts = dashboard_client.get("/api/v1/dashboard/alerts", headers=SUPPORT)

    assert operations.status_code == 200
    assert operations.json()["metadata"]["data_status"] == "partial"
    assert operations.json()["healthy_dependencies"] == 2
    assert alerts.status_code == 200
    codes = {item["code"] for item in alerts.json()["items"]}
    assert codes == {"dependency_unavailable", "inventory_low_stock", "inventory_out_of_stock"}


def test_operations_admin_is_authorized_and_customer_is_forbidden(
    dashboard_client: ApiClient,
) -> None:
    assert dashboard_client.get("/api/v1/dashboard/summary", headers=OPS).status_code == 200
    denied = dashboard_client.get("/api/v1/dashboard/summary", headers=CUSTOMER)

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "forbidden"


def test_support_has_selected_read_access_but_not_executive_revenue(
    dashboard_client: ApiClient,
) -> None:
    assert dashboard_client.get("/api/v1/dashboard/inventory", headers=SUPPORT).status_code == 200
    assert dashboard_client.get("/api/v1/dashboard/operations", headers=SUPPORT).status_code == 200
    assert dashboard_client.get("/api/v1/dashboard/orders", headers=SUPPORT).status_code == 403
    assert dashboard_client.get("/api/v1/dashboard/summary", headers=SUPPORT).status_code == 403


def test_missing_and_invalid_token_are_rejected(dashboard_client: ApiClient) -> None:
    missing = dashboard_client.get("/api/v1/dashboard/summary")
    invalid = dashboard_client.get(
        "/api/v1/dashboard/summary", headers={"Authorization": "Bearer invalid-token"}
    )

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.headers["WWW-Authenticate"] == "Bearer"


def test_prometheus_metrics_use_bounded_routes(dashboard_client: ApiClient) -> None:
    dashboard_client.get("/api/v1/dashboard/summary", headers=OPS)

    metrics = dashboard_client.get("/metrics")

    assert metrics.status_code == 200
    assert "shopsphere_http_requests_total" in metrics.text
    assert 'route="/api/v1/dashboard/summary"' in metrics.text
    assert "subject-operations-token" not in metrics.text
    assert "dashboard-test" not in metrics.text
    assert "process_resident_memory_bytes" in metrics.text


def test_partial_dashboard_aggregation_is_counted(
    dashboard_client: ApiClient, sources: FakeSources
) -> None:
    sources.customer_error = SourceTimeoutError()
    dashboard_client.get("/api/v1/dashboard/summary", headers=OPS)

    metrics = dashboard_client.get("/metrics").text

    assert "shopsphere_dashboard_aggregations_total" in metrics
    assert 'endpoint="summary"' in metrics
    assert 'data_status="partial"' in metrics
