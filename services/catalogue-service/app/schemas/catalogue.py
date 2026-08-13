"""Validated API contracts for Product Catalogue."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from app.domain.models import ProductStatus

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
CategoryName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)
]
Description = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)
]
Slug = Annotated[
    str,
    BeforeValidator(lambda value: value.strip().lower() if isinstance(value, str) else value),
    StringConstraints(
        min_length=2,
        max_length=80,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    ),
]
Sku = Annotated[
    str,
    BeforeValidator(lambda value: value.strip().upper() if isinstance(value, str) else value),
    StringConstraints(
        min_length=2,
        max_length=64,
        pattern=r"^[A-Z0-9][A-Z0-9._-]*$",
    ),
]
Money = Annotated[Decimal, Field(gt=0, max_digits=19, decimal_places=4)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CategoryCreate(StrictModel):
    name: CategoryName
    slug: Slug
    description: Description | None = None
    is_active: bool = True
    parent_id: UUID | None = None


class CategoryUpdate(StrictModel):
    name: CategoryName | None = None
    slug: Slug | None = None
    description: Description | None = None
    is_active: bool | None = None
    parent_id: UUID | None = None

    @model_validator(mode="after")
    def require_change(self) -> CategoryUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one category field is required")
        for field_name in ("name", "slug", "is_active"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class CategoryResponse(StrictModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    is_active: bool
    parent_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CategoryListResponse(StrictModel):
    items: list[CategoryResponse]
    offset: int
    limit: int
    total: int


class ProductCreate(StrictModel):
    sku: Sku
    name: Name
    description: Description | None = None
    category_id: UUID
    status: ProductStatus = ProductStatus.DRAFT
    is_searchable: bool = False


class ProductUpdate(StrictModel):
    name: Name | None = None
    description: Description | None = None
    category_id: UUID | None = None
    status: ProductStatus | None = None
    is_searchable: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> ProductUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one product field is required")
        for field_name in ("name", "category_id", "status", "is_searchable"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} cannot be null")
        return self


class ProductResponse(StrictModel):
    id: UUID
    sku: str
    name: str
    description: str | None
    category_id: UUID
    status: ProductStatus
    is_searchable: bool
    created_at: datetime
    updated_at: datetime


class ProductListResponse(StrictModel):
    items: list[ProductResponse]
    offset: int
    limit: int
    total: int


class PriceUpdate(StrictModel):
    amount: Money


class PriceResponse(StrictModel):
    id: UUID
    product_id: UUID
    amount: Decimal
    currency_code: str
    is_active: bool
    effective_from: datetime
    effective_to: datetime | None
    created_at: datetime
    updated_at: datetime


class PriceListResponse(StrictModel):
    items: list[PriceResponse]
