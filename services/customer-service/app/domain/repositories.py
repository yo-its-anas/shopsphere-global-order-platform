"""Repository and transaction contracts owned by the domain boundary."""

from __future__ import annotations

from types import TracebackType
from typing import Protocol
from uuid import UUID

from app.domain.models import CustomerAddress, CustomerAuditEvent, CustomerProfile


class CustomerRepository(Protocol):
    def add_profile(self, profile: CustomerProfile) -> None: ...

    async def get_profile_by_id(self, customer_id: UUID) -> CustomerProfile | None: ...

    async def get_profile_by_subject(self, subject: str) -> CustomerProfile | None: ...

    async def list_profiles(self, offset: int, limit: int) -> list[CustomerProfile]: ...

    async def update_profile(self, profile: CustomerProfile) -> None: ...

    def add_address(self, address: CustomerAddress) -> None: ...

    async def get_address_for_customer(
        self, customer_id: UUID, address_id: UUID
    ) -> CustomerAddress | None: ...

    async def list_addresses(self, customer_id: UUID) -> list[CustomerAddress]: ...

    async def update_address(self, address: CustomerAddress) -> None: ...

    async def clear_default_addresses(self, customer_id: UUID) -> None: ...

    async def delete_address(self, address: CustomerAddress) -> None: ...

    def add_audit_event(self, event: CustomerAuditEvent) -> None: ...

    async def list_audit_events(
        self, customer_id: UUID, offset: int, limit: int
    ) -> list[CustomerAuditEvent]: ...


class UnitOfWork(Protocol):
    customers: CustomerRepository

    async def __aenter__(self) -> UnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def flush(self) -> None: ...
