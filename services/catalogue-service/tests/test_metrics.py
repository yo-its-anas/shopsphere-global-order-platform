"""Catalogue HTTP, cache, and reservation metric tests."""

from typing import Any
from uuid import uuid4


def test_metrics_count_cache_and_failed_reservation_without_high_cardinality(
    client: Any, auth_headers: Any
) -> None:
    client.get("/api/v1/categories", headers=auth_headers("customer"))
    client.get("/api/v1/categories", headers=auth_headers("customer"))
    dynamic_id = str(uuid4())
    rejected = client.post(
        "/api/v1/inventory/reservations",
        headers=auth_headers("order_service"),
        json={
            "product_id": dynamic_id,
            "quantity": 1,
            "external_reference": "metrics-safe-reference",
        },
    )
    assert rejected.status_code == 404
    assert client.get(f"/api/v1/products/{dynamic_id}", headers=auth_headers()).status_code == 404

    body = client.get("/metrics").text
    assert "shopsphere_http_requests_total" in body
    assert 'route="/api/v1/products/{product_id}"' in body
    assert "shopsphere_catalogue_cache_requests_total" in body
    assert 'family="category-list"' in body
    assert 'result="miss"' in body
    assert 'result="hit"' in body
    assert "shopsphere_inventory_reservation_attempts_total" in body
    assert "shopsphere_inventory_reservation_results_total" in body
    assert 'result="failure"' in body
    assert dynamic_id not in body
    assert "metrics-safe-reference" not in body
