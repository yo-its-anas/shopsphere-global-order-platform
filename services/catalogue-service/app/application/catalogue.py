"""Product category, product, pricing, and search use cases."""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import replace
from decimal import Decimal
from uuid import UUID

from app.core.errors import (
    AuthorizationError,
    ConflictError,
    InvalidOperationError,
    ResourceNotFoundError,
)
from app.core.security import Principal, Role
from app.domain.models import Product, ProductCategory, ProductPrice, ProductStatus, utc_now
from app.domain.repositories import UnitOfWork

logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], UnitOfWork]


def normalize_slug(value: str) -> str:
    return value.strip().lower()


def normalize_sku(value: str) -> str:
    return value.strip().upper()


class CatalogueService:
    """Application policy for catalogue mutations and role-aware read visibility."""

    def __init__(
        self, unit_of_work_factory: UnitOfWorkFactory, supported_currencies: frozenset[str]
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._supported_currencies = supported_currencies

    @staticmethod
    def _is_privileged(actor: Principal) -> bool:
        return actor.has_any_role(Role.SUPPORT, Role.OPERATIONS_ADMIN)

    async def _require_active_category_chain(
        self, repository: object, category: ProductCategory
    ) -> None:
        current = category
        visited: set[UUID] = set()
        while True:
            if not current.is_active:
                raise ResourceNotFoundError
            if current.parent_id is None:
                return
            if current.id in visited:
                raise ConflictError
            visited.add(current.id)
            current = await repository.get_category(current.parent_id)  # type: ignore[attr-defined]
            if current is None:
                raise ResourceNotFoundError

    async def _validate_parent(
        self,
        repository: object,
        parent_id: UUID | None,
        category_id: UUID | None = None,
    ) -> None:
        if parent_id is None:
            return
        if parent_id == category_id:
            raise InvalidOperationError
        visited: set[UUID] = set()
        current_id: UUID | None = parent_id
        while current_id is not None:
            if current_id == category_id or current_id in visited:
                raise InvalidOperationError
            visited.add(current_id)
            parent = await repository.get_category(current_id)  # type: ignore[attr-defined]
            if parent is None:
                raise ResourceNotFoundError
            if not parent.is_active:
                raise ConflictError
            current_id = parent.parent_id

    async def create_category(
        self, actor: Principal, values: dict[str, object], correlation_id: str
    ) -> ProductCategory:
        slug = normalize_slug(str(values["slug"]))
        async with self._unit_of_work_factory() as work:
            if await work.catalogue.get_category_by_slug(slug):
                raise ConflictError
            parent_id = values.get("parent_id")
            await self._validate_parent(
                work.catalogue, parent_id if isinstance(parent_id, UUID) else None
            )
            category = ProductCategory(
                name=str(values["name"]).strip(),
                slug=slug,
                description=values.get("description"),  # type: ignore[arg-type]
                is_active=bool(values.get("is_active", True)),
                parent_id=parent_id if isinstance(parent_id, UUID) else None,
            )
            work.catalogue.add_category(category)
            await work.flush()
            await work.commit()
        logger.info(
            "category_created",
            extra={
                "event": "category_created",
                "category_id": str(category.id),
                "actor_subject": actor.subject,
                "correlation_id": correlation_id,
            },
        )
        return category

    async def list_categories(
        self, actor: Principal, active: bool | None, offset: int, limit: int
    ) -> tuple[Sequence[ProductCategory], int]:
        effective_active = active if self._is_privileged(actor) else True
        async with self._unit_of_work_factory() as work:
            return await work.catalogue.list_categories(
                active=effective_active, offset=offset, limit=limit
            )

    async def get_category(self, actor: Principal, category_id: UUID) -> ProductCategory:
        async with self._unit_of_work_factory() as work:
            category = await work.catalogue.get_category(category_id)
            if category is None or (not self._is_privileged(actor) and not category.is_active):
                raise ResourceNotFoundError
            return category

    async def update_category(
        self,
        actor: Principal,
        category_id: UUID,
        changes: dict[str, object],
        correlation_id: str,
    ) -> ProductCategory:
        async with self._unit_of_work_factory() as work:
            category = await work.catalogue.get_category(category_id)
            if category is None:
                raise ResourceNotFoundError
            if "slug" in changes:
                new_slug = normalize_slug(str(changes["slug"]))
                duplicate = await work.catalogue.get_category_by_slug(new_slug)
                if duplicate is not None and duplicate.id != category.id:
                    raise ConflictError
                changes["slug"] = new_slug
            if "name" in changes:
                changes["name"] = str(changes["name"]).strip()
            if "parent_id" in changes:
                parent_id = changes["parent_id"]
                await self._validate_parent(
                    work.catalogue,
                    parent_id if isinstance(parent_id, UUID) else None,
                    category.id,
                )
            category = replace(category, **changes, updated_at=utc_now())
            await work.catalogue.update_category(category)
            await work.flush()
            await work.commit()
        logger.info(
            "category_updated",
            extra={
                "event": "category_updated",
                "category_id": str(category.id),
                "actor_subject": actor.subject,
                "correlation_id": correlation_id,
            },
        )
        return category

    async def create_product(
        self, actor: Principal, values: dict[str, object], correlation_id: str
    ) -> Product:
        sku = normalize_sku(str(values["sku"]))
        category_id = values["category_id"]
        if not isinstance(category_id, UUID):
            raise InvalidOperationError
        async with self._unit_of_work_factory() as work:
            if await work.catalogue.get_product_by_sku(sku):
                raise ConflictError
            category = await work.catalogue.get_category(category_id)
            if category is None:
                raise ResourceNotFoundError
            await self._require_active_category_chain(work.catalogue, category)
            status = values.get("status", ProductStatus.DRAFT)
            if not isinstance(status, ProductStatus):
                raise InvalidOperationError
            searchable = bool(values.get("is_searchable", False))
            if status is not ProductStatus.ACTIVE:
                searchable = False
            product = Product(
                sku=sku,
                name=str(values["name"]).strip(),
                description=values.get("description"),  # type: ignore[arg-type]
                category_id=category_id,
                status=status,
                is_searchable=searchable,
            )
            work.catalogue.add_product(product)
            await work.flush()
            await work.commit()
        logger.info(
            "product_created",
            extra={
                "event": "product_created",
                "product_id": str(product.id),
                "actor_subject": actor.subject,
                "correlation_id": correlation_id,
            },
        )
        return product

    async def _visible_product(
        self, repository: object, actor: Principal, product_id: UUID
    ) -> Product:
        product = await repository.get_product(product_id)  # type: ignore[attr-defined]
        if product is None:
            raise ResourceNotFoundError
        if not self._is_privileged(actor):
            if product.status is not ProductStatus.ACTIVE or not product.is_searchable:
                raise ResourceNotFoundError
            category = await repository.get_category(product.category_id)  # type: ignore[attr-defined]
            if category is None:
                raise ResourceNotFoundError
            await self._require_active_category_chain(repository, category)
        return product

    async def get_product(self, actor: Principal, product_id: UUID) -> Product:
        async with self._unit_of_work_factory() as work:
            return await self._visible_product(work.catalogue, actor, product_id)

    async def list_products(
        self,
        actor: Principal,
        *,
        query: str | None,
        sku: str | None,
        category_id: UUID | None,
        status: ProductStatus | None,
        offset: int,
        limit: int,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[Sequence[Product], int]:
        privileged = self._is_privileged(actor)
        async with self._unit_of_work_factory() as work:
            return await work.catalogue.list_products(
                query=query.strip() if query else None,
                sku=normalize_sku(sku) if sku else None,
                category_id=category_id,
                status=status if privileged else ProductStatus.ACTIVE,
                searchable=None if privileged else True,
                require_active_category=not privileged,
                offset=offset,
                limit=limit,
                sort_by=sort_by,
                sort_direction=sort_direction,
            )

    async def update_product(
        self,
        actor: Principal,
        product_id: UUID,
        changes: dict[str, object],
        correlation_id: str,
    ) -> Product:
        async with self._unit_of_work_factory() as work:
            product = await work.catalogue.get_product(product_id)
            if product is None:
                raise ResourceNotFoundError
            if "category_id" in changes:
                category_id = changes["category_id"]
                if not isinstance(category_id, UUID):
                    raise InvalidOperationError
                category = await work.catalogue.get_category(category_id)
                if category is None:
                    raise ResourceNotFoundError
                await self._require_active_category_chain(work.catalogue, category)
            if "name" in changes:
                changes["name"] = str(changes["name"]).strip()
            new_status = changes.get("status", product.status)
            if new_status is not ProductStatus.ACTIVE:
                changes["is_searchable"] = False
            product = replace(product, **changes, updated_at=utc_now())
            await work.catalogue.update_product(product)
            await work.flush()
            await work.commit()
        logger.info(
            "product_updated",
            extra={
                "event": "product_updated",
                "product_id": str(product.id),
                "actor_subject": actor.subject,
                "correlation_id": correlation_id,
            },
        )
        return product

    async def deactivate_product(
        self, actor: Principal, product_id: UUID, correlation_id: str
    ) -> Product:
        return await self.update_product(
            actor,
            product_id,
            {"status": ProductStatus.INACTIVE, "is_searchable": False},
            correlation_id,
        )

    async def list_prices(
        self, actor: Principal, product_id: UUID, include_history: bool
    ) -> Sequence[ProductPrice]:
        if include_history and not self._is_privileged(actor):
            raise AuthorizationError
        async with self._unit_of_work_factory() as work:
            await self._visible_product(work.catalogue, actor, product_id)
            return await work.catalogue.list_prices(product_id, active_only=not include_history)

    async def set_price(
        self,
        actor: Principal,
        product_id: UUID,
        currency_code: str,
        amount: Decimal,
        correlation_id: str,
    ) -> ProductPrice:
        currency = currency_code.upper()
        if currency not in self._supported_currencies:
            raise InvalidOperationError
        changed_at = utc_now()
        async with self._unit_of_work_factory() as work:
            if await work.catalogue.get_product(product_id) is None:
                raise ResourceNotFoundError
            await work.catalogue.close_active_price(product_id, currency, changed_at)
            price = ProductPrice(
                product_id=product_id,
                amount=amount,
                currency_code=currency,
                effective_from=changed_at,
            )
            work.catalogue.add_price(price)
            await work.flush()
            await work.commit()
        logger.info(
            "price_changed",
            extra={
                "event": "price_changed",
                "product_id": str(product_id),
                "currency_code": currency,
                "actor_subject": actor.subject,
                "correlation_id": correlation_id,
            },
        )
        return price
