"""SQLAlchemy implementations of Product Catalogue repository contracts."""

from __future__ import annotations

from datetime import datetime
from types import TracebackType
from uuid import UUID

from sqlalchemy import Select, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import Product, ProductCategory, ProductPrice, ProductStatus
from app.infrastructure.orm_models import ProductCategoryRecord, ProductPriceRecord, ProductRecord


def _category_from_record(record: ProductCategoryRecord) -> ProductCategory:
    return ProductCategory(
        id=record.id,
        name=record.name,
        slug=record.slug,
        description=record.description,
        is_active=record.is_active,
        parent_id=record.parent_id,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _product_from_record(record: ProductRecord) -> Product:
    return Product(
        id=record.id,
        sku=record.sku,
        name=record.name,
        description=record.description,
        category_id=record.category_id,
        status=ProductStatus(record.status),
        is_searchable=record.is_searchable,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _price_from_record(record: ProductPriceRecord) -> ProductPrice:
    return ProductPrice(
        id=record.id,
        product_id=record.product_id,
        amount=record.amount,
        currency_code=record.currency_code,
        is_active=record.is_active,
        effective_from=record.effective_from,
        effective_to=record.effective_to,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


class SqlAlchemyCatalogueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_category(self, category: ProductCategory) -> None:
        self._session.add(
            ProductCategoryRecord(
                id=category.id,
                name=category.name,
                slug=category.slug,
                description=category.description,
                is_active=category.is_active,
                parent_id=category.parent_id,
                created_at=category.created_at,
                updated_at=category.updated_at,
            )
        )

    async def get_category(self, category_id: UUID) -> ProductCategory | None:
        record = await self._session.get(ProductCategoryRecord, category_id)
        return _category_from_record(record) if record else None

    async def get_category_by_slug(self, slug: str) -> ProductCategory | None:
        record = await self._session.scalar(
            select(ProductCategoryRecord).where(ProductCategoryRecord.slug == slug)
        )
        return _category_from_record(record) if record else None

    async def list_categories(
        self, *, active: bool | None, offset: int, limit: int
    ) -> tuple[list[ProductCategory], int]:
        statement: Select[tuple[ProductCategoryRecord]] = select(ProductCategoryRecord)
        if active is not None:
            statement = statement.where(ProductCategoryRecord.is_active.is_(active))
        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        records = await self._session.scalars(
            statement.order_by(ProductCategoryRecord.name, ProductCategoryRecord.id)
            .offset(offset)
            .limit(limit)
        )
        return [_category_from_record(record) for record in records], int(total or 0)

    async def update_category(self, category: ProductCategory) -> None:
        record = await self._session.get(ProductCategoryRecord, category.id)
        if record is None:
            return
        record.name = category.name
        record.slug = category.slug
        record.description = category.description
        record.is_active = category.is_active
        record.parent_id = category.parent_id
        record.updated_at = category.updated_at

    def add_product(self, product: Product) -> None:
        self._session.add(
            ProductRecord(
                id=product.id,
                sku=product.sku,
                name=product.name,
                description=product.description,
                category_id=product.category_id,
                status=product.status.value,
                is_searchable=product.is_searchable,
                created_at=product.created_at,
                updated_at=product.updated_at,
            )
        )

    async def get_product(self, product_id: UUID) -> Product | None:
        record = await self._session.get(ProductRecord, product_id)
        return _product_from_record(record) if record else None

    async def get_product_by_sku(self, sku: str) -> Product | None:
        record = await self._session.scalar(select(ProductRecord).where(ProductRecord.sku == sku))
        return _product_from_record(record) if record else None

    async def list_products(
        self,
        *,
        query: str | None,
        sku: str | None,
        category_id: UUID | None,
        status: ProductStatus | None,
        searchable: bool | None,
        require_active_category: bool,
        offset: int,
        limit: int,
        sort_by: str,
        sort_direction: str,
    ) -> tuple[list[Product], int]:
        statement: Select[tuple[ProductRecord]] = select(ProductRecord)
        if require_active_category:
            statement = statement.join(
                ProductCategoryRecord, ProductCategoryRecord.id == ProductRecord.category_id
            ).where(ProductCategoryRecord.is_active.is_(True))
        if query:
            pattern = f"%{query}%"
            statement = statement.where(
                or_(
                    ProductRecord.name.ilike(pattern),
                    ProductRecord.sku.ilike(pattern),
                    ProductRecord.description.ilike(pattern),
                )
            )
        if sku:
            statement = statement.where(ProductRecord.sku == sku)
        if category_id:
            statement = statement.where(ProductRecord.category_id == category_id)
        if status:
            statement = statement.where(ProductRecord.status == status.value)
        if searchable is not None:
            statement = statement.where(ProductRecord.is_searchable.is_(searchable))

        total = await self._session.scalar(select(func.count()).select_from(statement.subquery()))
        sort_columns = {
            "created_at": ProductRecord.created_at,
            "name": ProductRecord.name,
            "sku": ProductRecord.sku,
            "updated_at": ProductRecord.updated_at,
        }
        sort_column = sort_columns[sort_by]
        ordering = sort_column.desc() if sort_direction == "desc" else sort_column.asc()
        records = await self._session.scalars(
            statement.order_by(ordering, ProductRecord.id.asc()).offset(offset).limit(limit)
        )
        return [_product_from_record(record) for record in records], int(total or 0)

    async def update_product(self, product: Product) -> None:
        record = await self._session.get(ProductRecord, product.id)
        if record is None:
            return
        record.name = product.name
        record.description = product.description
        record.category_id = product.category_id
        record.status = product.status.value
        record.is_searchable = product.is_searchable
        record.updated_at = product.updated_at

    def add_price(self, price: ProductPrice) -> None:
        self._session.add(
            ProductPriceRecord(
                id=price.id,
                product_id=price.product_id,
                amount=price.amount,
                currency_code=price.currency_code,
                is_active=price.is_active,
                effective_from=price.effective_from,
                effective_to=price.effective_to,
                created_at=price.created_at,
                updated_at=price.updated_at,
            )
        )

    async def list_prices(self, product_id: UUID, *, active_only: bool) -> list[ProductPrice]:
        statement = select(ProductPriceRecord).where(ProductPriceRecord.product_id == product_id)
        if active_only:
            statement = statement.where(ProductPriceRecord.is_active.is_(True))
        records = await self._session.scalars(
            statement.order_by(
                ProductPriceRecord.currency_code,
                ProductPriceRecord.effective_from.desc(),
                ProductPriceRecord.id.desc(),
            )
        )
        return [_price_from_record(record) for record in records]

    async def close_active_price(
        self, product_id: UUID, currency_code: str, effective_to: datetime
    ) -> None:
        await self._session.execute(
            update(ProductPriceRecord)
            .where(
                ProductPriceRecord.product_id == product_id,
                ProductPriceRecord.currency_code == currency_code,
                ProductPriceRecord.is_active.is_(True),
            )
            .values(is_active=False, effective_to=effective_to, updated_at=effective_to)
        )


class SqlAlchemyUnitOfWork:
    """One database transaction for one catalogue operation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.catalogue = SqlAlchemyCatalogueRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        if exc_type is not None:
            await self._session.rollback()
        await self._session.close()

    async def flush(self) -> None:
        if self._session is not None:
            await self._session.flush()

    async def commit(self) -> None:
        if self._session is not None:
            await self._session.commit()
