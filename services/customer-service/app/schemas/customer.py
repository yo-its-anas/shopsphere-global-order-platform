"""Validated public contracts for customer APIs."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domain.models import (
    AccountStatusReason,
    ActivityCategory,
    ActivityResult,
    ActivitySource,
    CustomerStatus,
)

_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_PHONE_PATTERN = re.compile(r"^\+?[1-9][0-9 .()\-]{6,24}$")
_POSTAL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 .\-]{1,19}$")


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _validate_email(value: str) -> str:
    normalized = value.casefold()
    if len(normalized) > 320 or not _EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("email must be a valid address")
    return normalized


def _validate_phone(value: str | None) -> str | None:
    if value is not None and not _PHONE_PATTERN.fullmatch(value):
        raise ValueError("phone must be a valid international-style number")
    return value


class ProfileCreate(ApiModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: str
    phone: str | None = None

    _email = field_validator("email")(_validate_email)
    _phone = field_validator("phone")(_validate_phone)


class ProfileUpdate(ApiModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = None
    phone: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        return _validate_email(value) if value is not None else None

    _phone = field_validator("phone")(_validate_phone)

    @model_validator(mode="after")
    def require_change(self) -> ProfileUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one profile field must be supplied")
        return self


class ProfileResponse(ApiModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    phone: str | None
    status: CustomerStatus
    created_at: datetime
    updated_at: datetime


class ProfileProvisioningResponse(ApiModel):
    profile: ProfileResponse
    provisioned: bool


class AddressCreate(ApiModel):
    label: str = Field(min_length=1, max_length=50)
    recipient_name: str = Field(min_length=1, max_length=200)
    line1: str = Field(min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str = Field(min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(min_length=2, max_length=20)
    country_code: str = Field(min_length=2, max_length=2)
    phone: str | None = None
    is_default: bool = False

    _phone = field_validator("phone")(_validate_phone)

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str) -> str:
        if not _POSTAL_PATTERN.fullmatch(value):
            raise ValueError("postal_code contains unsupported characters")
        return value

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str) -> str:
        normalized = value.upper()
        if not normalized.isalpha() or not normalized.isascii():
            raise ValueError("country_code must contain two ASCII letters")
        return normalized


class AddressUpdate(ApiModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)
    recipient_name: str | None = Field(default=None, min_length=1, max_length=200)
    line1: str | None = Field(default=None, min_length=1, max_length=200)
    line2: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, min_length=2, max_length=20)
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    phone: str | None = None

    _phone = field_validator("phone")(_validate_phone)

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, value: str | None) -> str | None:
        if value is not None and not _POSTAL_PATTERN.fullmatch(value):
            raise ValueError("postal_code contains unsupported characters")
        return value

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.upper()
        if not normalized.isalpha() or not normalized.isascii():
            raise ValueError("country_code must contain two ASCII letters")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> AddressUpdate:
        if not self.model_fields_set:
            raise ValueError("at least one address field must be supplied")
        return self


class AddressResponse(ApiModel):
    id: UUID
    label: str
    recipient_name: str
    line1: str
    line2: str | None
    city: str
    region: str | None
    postal_code: str
    country_code: str
    phone: str | None
    is_default: bool
    created_at: datetime
    updated_at: datetime


class AccountStatusUpdate(ApiModel):
    status: CustomerStatus
    reason_code: AccountStatusReason


class AuditEventResponse(ApiModel):
    id: UUID
    customer_id: UUID
    actor_subject: str
    action: str
    entity_type: str
    entity_id: UUID | None
    occurred_at: datetime
    correlation_id: str
    metadata: dict[str, Any]


class ProfileListResponse(ApiModel):
    items: list[ProfileResponse]
    offset: int
    limit: int


class AuditEventListResponse(ApiModel):
    items: list[AuditEventResponse]
    offset: int
    limit: int


class ActivityEventResponse(ApiModel):
    timestamp: datetime
    event_category: ActivityCategory
    action: str
    source: ActivitySource
    result: ActivityResult
    context: dict[str, Any]


class ActivityListResponse(ApiModel):
    items: list[ActivityEventResponse]
    offset: int
    limit: int
