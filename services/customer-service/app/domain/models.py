"""Persistence-independent customer domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


class CustomerStatus(str, Enum):
    """Governed customer account lifecycle states."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class AccountStatusReason(str, Enum):
    """Safe, governed rationale categories for administrative status changes."""

    CUSTOMER_REQUEST = "customer_request"
    RISK_REVIEW = "risk_review"
    POLICY_VIOLATION = "policy_violation"
    ADMINISTRATIVE_CORRECTION = "administrative_correction"
    OTHER = "other"


class ActivityCategory(str, Enum):
    """Stable categories presented independently of source payload formats."""

    CUSTOMER_DOMAIN = "customer_domain"
    AUTHENTICATION = "authentication"
    IDENTITY_ADMINISTRATION = "identity_administration"


class ActivitySource(str, Enum):
    """Systems of record contributing to the customer activity view."""

    CUSTOMER_SERVICE = "customer_service"
    KEYCLOAK = "keycloak"


class ActivityResult(str, Enum):
    """Safe, source-neutral activity outcomes."""

    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(slots=True)
class CustomerProfile:
    """Customer-owned business profile linked to one external identity."""

    identity_provider_subject: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    status: CustomerStatus = CustomerStatus.ACTIVE
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CustomerAddress:
    """Postal address owned by a customer profile."""

    customer_id: UUID
    label: str
    recipient_name: str
    line1: str
    city: str
    postal_code: str
    country_code: str
    line2: str | None = None
    region: str | None = None
    phone: str | None = None
    is_default: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class CustomerAuditEvent:
    """Append-only record of a customer-domain action."""

    customer_id: UUID
    actor_subject: str
    action: str
    entity_type: str
    correlation_id: str
    safe_metadata: dict[str, Any] = field(default_factory=dict)
    entity_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class CustomerActivity:
    """Safe normalized projection; source records retain source-of-truth ownership."""

    timestamp: datetime
    category: ActivityCategory
    action: str
    source: ActivitySource
    result: ActivityResult
    context: dict[str, Any] = field(default_factory=dict)
