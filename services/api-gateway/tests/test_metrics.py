"""Prometheus contract, cardinality, and gateway upstream metric tests."""

from typing import Any

import httpx2


def test_metrics_are_safe_bounded_and_count_http_and_upstream_results(
    client: Any, upstream_client: Any
) -> None:
    dynamic_id = "8e072573-653f-416d-a238-06e8230d42c4"
    sensitive_marker = "signed.jwt.must-not-appear"
    successful = client.get(
        f"/api/v1/admin/customers/{dynamic_id}/activity",
        headers={"Authorization": f"Bearer {sensitive_marker}"},
    )
    assert successful.status_code == 200

    upstream_client.error = httpx2.ConnectError(
        "private dependency detail",
        request=httpx2.Request("GET", "http://customer-service/api/v1/customers/me"),
    )
    assert client.get("/api/v1/customers/me").status_code == 503
    assert client.get("/not-a-route").status_code == 404

    body = client.get("/metrics").text
    assert "shopsphere_http_requests_total" in body
    assert 'route="/api/v1/admin/customers/{customer_id}/activity"' in body
    assert 'status_class="4xx"' in body
    assert "shopsphere_gateway_upstream_requests_total" in body
    assert 'result="success"' in body
    assert 'result="unavailable"' in body
    assert dynamic_id not in body
    assert sensitive_marker not in body
    assert "private dependency detail" not in body
    assert "process_resident_memory_bytes" in body
