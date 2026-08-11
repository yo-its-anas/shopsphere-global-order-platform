"""Persistence-independent Product Catalogue domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProductStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISCONTINUED = "discontinued"


@dataclass(slots=True)
class ProductCategory:
    name: str
    slug: str
    description: str | None = None
    is_active: bool = True
    parent_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class Product:
    sku: str
    name: str
    category_id: UUID
    description: str | None = None
    status: ProductStatus = ProductStatus.DRAFT
    is_searchable: bool = False
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class ProductPrice:
    product_id: UUID
    amount: Decimal
    currency_code: str
    is_active: bool = True
    effective_from: datetime = field(default_factory=utc_now)
    effective_to: datetime | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
