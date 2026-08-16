"""Shared test fixtures."""

from collections.abc import Iterator

import pytest

from app.core.config import Settings
from app.main import create_app
from tests.support import ApiClient, FakeSources, FakeTokenVerifier


@pytest.fixture
def settings() -> Settings:
    return Settings(
        service_name="analytics-service",
        service_version="0.1.0",
        environment="test",
        log_level="WARNING",
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[ApiClient]:
    test_client = ApiClient(create_app(settings))
    yield test_client
    test_client.close()


@pytest.fixture
def sources() -> FakeSources:
    return FakeSources()


@pytest.fixture
def dashboard_client(settings: Settings, sources: FakeSources) -> Iterator[ApiClient]:
    test_client = ApiClient(
        create_app(
            settings,
            token_verifier=FakeTokenVerifier(),
            dashboard_sources=sources,
        )
    )
    yield test_client
    test_client.close()
