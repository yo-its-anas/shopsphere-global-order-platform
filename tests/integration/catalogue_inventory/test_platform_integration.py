"""Opt-in Redis and Kafka/outbox platform integration tests."""

from __future__ import annotations

import secrets
from typing import Any

import pytest

from customer_identity.http import assert_status

from .conftest import CatalogueContext
from .platform import PlatformInspector

pytestmark = [
    pytest.mark.catalogue_inventory_integration,
    pytest.mark.catalogue_platform_integration,
]

_SENSITIVE_KEYS = {
    "password",
    "credential",
    "credentials",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "client_secret",
}


def _assert_safe(value: Any) -> None:
    if isinstance(value, dict):
        assert not ({str(key).casefold() for key in value} & _SENSITIVE_KEYS)
        for nested in value.values():
            _assert_safe(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_safe(nested)


def test_redis_cache_miss_then_hit_is_observable(
    catalogue_context: CatalogueContext,
    platform_inspector: PlatformInspector,
) -> None:
    context = catalogue_context
    product = context.create_product(context.create_category()["id"])
    misses_before = platform_inspector.cache_log_count("cache_miss", "product")
    hits_before = platform_inspector.cache_log_count("cache_hit", "product")

    assert_status(context.api("customer", "GET", f"products/{product['id']}"), 200)
    assert_status(context.api("customer", "GET", f"products/{product['id']}"), 200)

    misses_after = platform_inspector.cache_log_count("cache_miss", "product")
    hits_after = platform_inspector.cache_log_count("cache_hit", "product")
    assert misses_after > misses_before
    assert hits_after > hits_before


def test_expected_versioned_event_is_eventually_published(
    catalogue_context: CatalogueContext,
    platform_inspector: PlatformInspector,
) -> None:
    context = catalogue_context
    correlation_id = f"catalogue-integration-event-{secrets.token_hex(8)}"
    product = context.create_product(
        context.create_category()["id"], request_id=correlation_id
    )
    events = platform_inspector.wait_for_published(correlation_id)
    assert len(events) == 1
    event = events[0]
    assert event["event_type"] == "catalogue.product.created.v1"
    assert event["event_version"] == 1
    assert event["correlation_id"] == correlation_id
    assert event["aggregate_id"] == product["id"]
    assert event["producer"] == "catalogue-service"
    assert event["published"] is True
    _assert_safe(event["payload"])


def test_redis_unavailable_falls_back_to_postgresql_when_explicitly_allowed(
    catalogue_context: CatalogueContext,
    platform_inspector: PlatformInspector,
) -> None:
    context = catalogue_context
    if not context.config.redis_outage_test:
        pytest.skip(
            "Controlled Redis outage was not authorized; set "
            "SHOPSPHERE_TEST_ALLOW_REDIS_OUTAGE=true in an isolated PoC window."
        )
    product = context.create_product(context.create_category()["id"])
    platform_inspector.scale("shopsphere-data", "deployment/redis", 0)
    try:
        platform_inspector.wait_for_ready_replicas(
            "shopsphere-data", "deployment/redis", 0
        )
        response = context.api("customer", "GET", f"products/{product['id']}")
        assert_status(response, 200)
        assert response.json()["id"] == product["id"]
    finally:
        platform_inspector.scale("shopsphere-data", "deployment/redis", 1)
        platform_inspector.wait_rollout("shopsphere-data", "deployment/redis")


def test_outbox_recovers_after_kafka_outage_when_explicitly_allowed(
    catalogue_context: CatalogueContext,
    platform_inspector: PlatformInspector,
) -> None:
    context = catalogue_context
    if not context.config.kafka_outage_test:
        pytest.skip(
            "Controlled Kafka outage was not authorized; set "
            "SHOPSPHERE_TEST_ALLOW_KAFKA_OUTAGE=true in an isolated PoC window."
        )
    correlation_id = f"catalogue-integration-retry-{secrets.token_hex(8)}"
    category = context.create_category()
    platform_inspector.scale("shopsphere-platform", "statefulset/kafka", 0)
    try:
        platform_inspector.wait_for_ready_replicas(
            "shopsphere-platform", "statefulset/kafka", 0
        )
        product = context.create_product(category["id"], request_id=correlation_id)
        pending = platform_inspector.outbox_events(correlation_id)
        assert pending
        assert pending[0]["aggregate_id"] == product["id"]
        assert pending[0]["status"] == "pending"
    finally:
        platform_inspector.scale("shopsphere-platform", "statefulset/kafka", 1)
        platform_inspector.wait_rollout("shopsphere-platform", "statefulset/kafka")
    published = platform_inspector.wait_for_published(
        correlation_id, timeout_seconds=60
    )
    assert published[0]["status"] == "published"
    assert published[0]["attempts"] >= 1
