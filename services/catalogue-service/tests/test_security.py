"""Focused tests for allow-listed Keycloak role extraction."""

import pytest

from app.core.errors import AuthenticationError
from app.core.security import Role, _principal_from_claims


def test_roles_are_allow_listed_from_realm_and_configured_client() -> None:
    principal = _principal_from_claims(
        {
            "sub": "catalogue-user",
            "realm_access": {"roles": ["customer", "offline_access", 123]},
            "resource_access": {
                "shopsphere-api": {"roles": ["support"]},
                "unrelated-client": {"roles": ["operations_admin"]},
            },
        },
        "shopsphere-api",
    )

    assert principal.roles == frozenset({"customer", "support"})
    assert principal.has_any_role(Role.CUSTOMER)
    assert not principal.has_any_role(Role.OPERATIONS_ADMIN)


def test_subject_is_required_and_bounded() -> None:
    with pytest.raises(AuthenticationError):
        _principal_from_claims({}, "shopsphere-api")
    with pytest.raises(AuthenticationError):
        _principal_from_claims({"sub": "x" * 256}, "shopsphere-api")
