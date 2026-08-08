"""SQLAlchemy implementations of customer repository contracts."""

from __future__ import annotations

from types import TracebackType
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.models import (
    CustomerAddress,
    CustomerAuditEvent,
    CustomerProfile,
    CustomerStatus,
    utc_now,
)
from app.infrastructure.orm_models import (
    CustomerAddressRecord,
    CustomerAuditEventRecord,
    CustomerProfileRecord,
)


def _profile_from_record(record: CustomerProfileRecord) -> CustomerProfile:
    return CustomerProfile(
        id=record.id,
        identity_provider_subject=record.identity_provider_subject,
        first_name=record.first_name,
        last_name=record.last_name,
        email=record.email,
        phone=record.phone,
        status=CustomerStatus(record.account_status),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _address_from_record(record: CustomerAddressRecord) -> CustomerAddress:
    return CustomerAddress(
        id=record.id,
        customer_id=record.customer_id,
        label=record.label,
        recipient_name=record.recipient_name,
        line1=record.line1,
        line2=record.line2,
        city=record.city,
        region=record.region,
        postal_code=record.postal_code,
        country_code=record.country_code,
        phone=record.phone,
        is_default=record.is_default,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _audit_from_record(record: CustomerAuditEventRecord) -> CustomerAuditEvent:
    return CustomerAuditEvent(
        id=record.id,
        customer_id=record.customer_id,
        actor_subject=record.actor_subject,
        action=record.action,
        entity_type=record.entity_type,
        entity_id=record.entity_id,
        occurred_at=record.occurred_at,
        correlation_id=record.correlation_id,
        safe_metadata=dict(record.safe_metadata),
    )


class SqlAlchemyCustomerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_profile(self, profile: CustomerProfile) -> None:
        self._session.add(
            CustomerProfileRecord(
                id=profile.id,
                identity_provider_subject=profile.identity_provider_subject,
                first_name=profile.first_name,
                last_name=profile.last_name,
                email=profile.email,
                phone=profile.phone,
                account_status=profile.status.value,
                created_at=profile.created_at,
                updated_at=profile.updated_at,
            )
        )

    async def provision_profile_if_absent(
        self, profile: CustomerProfile
    ) -> tuple[CustomerProfile, bool]:
        """Atomically insert one profile per identity-provider subject."""

        values = {
            "id": profile.id,
            "identity_provider_subject": profile.identity_provider_subject,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "email": profile.email,
            "phone": profile.phone,
            "account_status": profile.status.value,
            "created_at": profile.created_at,
            "updated_at": profile.updated_at,
        }
        dialect_name = self._session.get_bind().dialect.name
        if dialect_name == "postgresql":
            statement = (
                postgresql_insert(CustomerProfileRecord)
                .values(**values)
                .on_conflict_do_nothing(constraint="uq_customer_profiles_idp_subject")
                .returning(CustomerProfileRecord.id)
            )
        elif dialect_name == "sqlite":
            statement = (
                sqlite_insert(CustomerProfileRecord)
                .values(**values)
                .on_conflict_do_nothing(index_elements=["identity_provider_subject"])
                .returning(CustomerProfileRecord.id)
            )
        else:
            raise RuntimeError("Profile provisioning requires a supported SQL dialect")

        result = await self._session.execute(statement)
        if result.scalar_one_or_none() is not None:
            return profile, True

        existing = await self.get_profile_by_subject(profile.identity_provider_subject)
        if existing is None:
            raise RuntimeError("Identity conflict did not resolve to an existing profile")
        return existing, False

    async def get_profile_by_id(self, customer_id: UUID) -> CustomerProfile | None:
        record = await self._session.get(CustomerProfileRecord, customer_id)
        return _profile_from_record(record) if record else None

    async def get_profile_by_subject(self, subject: str) -> CustomerProfile | None:
        record = await self._session.scalar(
            select(CustomerProfileRecord).where(
                CustomerProfileRecord.identity_provider_subject == subject
            )
        )
        return _profile_from_record(record) if record else None

    async def list_profiles(self, offset: int, limit: int) -> list[CustomerProfile]:
        statement: Select[tuple[CustomerProfileRecord]] = (
            select(CustomerProfileRecord)
            .order_by(CustomerProfileRecord.created_at, CustomerProfileRecord.id)
            .offset(offset)
            .limit(limit)
        )
        records = await self._session.scalars(statement)
        return [_profile_from_record(record) for record in records]

    async def update_profile(self, profile: CustomerProfile) -> None:
        record = await self._session.get(CustomerProfileRecord, profile.id)
        if record is None:
            return
        record.first_name = profile.first_name
        record.last_name = profile.last_name
        record.email = profile.email
        record.phone = profile.phone
        record.account_status = profile.status.value
        record.updated_at = profile.updated_at

    def add_address(self, address: CustomerAddress) -> None:
        self._session.add(
            CustomerAddressRecord(
                id=address.id,
                customer_id=address.customer_id,
                label=address.label,
                recipient_name=address.recipient_name,
                line1=address.line1,
                line2=address.line2,
                city=address.city,
                region=address.region,
                postal_code=address.postal_code,
                country_code=address.country_code,
                phone=address.phone,
                is_default=address.is_default,
                created_at=address.created_at,
                updated_at=address.updated_at,
            )
        )

    async def get_address_for_customer(
        self, customer_id: UUID, address_id: UUID
    ) -> CustomerAddress | None:
        record = await self._session.scalar(
            select(CustomerAddressRecord).where(
                CustomerAddressRecord.id == address_id,
                CustomerAddressRecord.customer_id == customer_id,
            )
        )
        return _address_from_record(record) if record else None

    async def list_addresses(self, customer_id: UUID) -> list[CustomerAddress]:
        records = await self._session.scalars(
            select(CustomerAddressRecord)
            .where(CustomerAddressRecord.customer_id == customer_id)
            .order_by(
                CustomerAddressRecord.is_default.desc(),
                CustomerAddressRecord.created_at,
                CustomerAddressRecord.id,
            )
        )
        return [_address_from_record(record) for record in records]

    async def update_address(self, address: CustomerAddress) -> None:
        record = await self._session.get(CustomerAddressRecord, address.id)
        if record is None or record.customer_id != address.customer_id:
            return
        for attribute in (
            "label",
            "recipient_name",
            "line1",
            "line2",
            "city",
            "region",
            "postal_code",
            "country_code",
            "phone",
            "is_default",
            "updated_at",
        ):
            setattr(record, attribute, getattr(address, attribute))

    async def clear_default_addresses(self, customer_id: UUID) -> None:
        await self._session.execute(
            update(CustomerAddressRecord)
            .where(
                CustomerAddressRecord.customer_id == customer_id,
                CustomerAddressRecord.is_default.is_(True),
            )
            .values(is_default=False, updated_at=utc_now())
        )

    async def delete_address(self, address: CustomerAddress) -> None:
        record = await self._session.get(CustomerAddressRecord, address.id)
        if record is not None and record.customer_id == address.customer_id:
            await self._session.delete(record)

    def add_audit_event(self, event: CustomerAuditEvent) -> None:
        self._session.add(
            CustomerAuditEventRecord(
                id=event.id,
                customer_id=event.customer_id,
                actor_subject=event.actor_subject,
                action=event.action,
                entity_type=event.entity_type,
                entity_id=event.entity_id,
                occurred_at=event.occurred_at,
                correlation_id=event.correlation_id,
                safe_metadata=event.safe_metadata,
            )
        )

    async def list_audit_events(
        self, customer_id: UUID, offset: int, limit: int
    ) -> list[CustomerAuditEvent]:
        records = await self._session.scalars(
            select(CustomerAuditEventRecord)
            .where(CustomerAuditEventRecord.customer_id == customer_id)
            .order_by(
                CustomerAuditEventRecord.occurred_at.desc(),
                CustomerAuditEventRecord.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        return [_audit_from_record(record) for record in records]


class SqlAlchemyUnitOfWork:
    """One database transaction for one application operation."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self.customers = SqlAlchemyCustomerRepository(self._session)
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
