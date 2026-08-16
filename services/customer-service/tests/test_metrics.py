"""Prometheus endpoint and safe-cardinality tests."""

from typing import Any


def test_metrics_count_requests_errors_and_never_expose_dynamic_or_secret_values(
    client: Any,
) -> None:
    dynamic_id = "8e072573-653f-416d-a238-06e8230d42c4"
    sensitive_marker = "private.jwt.value"
    assert (
        client.get(
            f"/api/v1/admin/customers/{dynamic_id}",
            headers={"Authorization": f"Bearer {sensitive_marker}"},
        ).status_code
        == 401
    )
    assert client.get("/not-a-route").status_code == 404

    body = client.get("/metrics").text
    assert "shopsphere_http_requests_total" in body
    assert 'route="/api/v1/admin/customers/{customer_id}"' in body
    assert 'status_class="4xx"' in body
    assert dynamic_id not in body
    assert sensitive_marker not in body
    assert "process_resident_memory_bytes" in body
    assert "shopsphere_service_info" in body
