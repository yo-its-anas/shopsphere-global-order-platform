"""Customer profile, address, account-status, and audit use cases."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace
from typing import Any
from uuid import UUID

from app.core.errors import ConflictError, InvalidIdentityClaimsError, ResourceNotFoundError
from app.core.security import Principal
from app.domain.models import (
    AccountStatusReason,
    CustomerAddress,
    CustomerAuditEvent,
    CustomerProfile,
    CustomerStatus,
    utc_now,
)
from app.domain.repositories import UnitOfWork

UnitOfWorkFactory = Callable[[], UnitOfWork]
_IDENTITY_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class CustomerAccountService:
    """Application policy with transactionally consistent domain auditing."""

    def __init__(self, unit_of_work_factory: UnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    @staticmethod
    def _event(
        customer_id: UUID,
        actor: Principal,
        action: str,
        entity_type: str,
        correlation_id: str,
        entity_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CustomerAuditEvent:
        return CustomerAuditEvent(
            customer_id=customer_id,
            actor_subject=actor.subject,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            correlation_id=correlation_id,
            safe_metadata=metadata or {},
        )

    @staticmethod
    def _require_mutable(profile: CustomerProfile) -> None:
        if profile.status is not CustomerStatus.ACTIVE:
            raise ConflictError

    @staticmethod
    def _profile_values_from_identity(actor: Principal) -> dict[str, str]:
        first_name = (actor.given_name or "").strip()
        last_name = (actor.family_name or "").strip()
        email = (actor.email or "").strip().casefold()
        names_are_safe = all(
            value and len(value) <= 100 and not any(ord(character) < 32 for character in value)
            for value in (first_name, last_name)
        )
        if not names_are_safe or len(email) > 320 or not _IDENTITY_EMAIL_PATTERN.fullmatch(email):
            raise InvalidIdentityClaimsError
        return {"first_name": first_name, "last_name": last_name, "email": email}

    async def provision_authenticated_profile(
        self, actor: Principal, correlation_id: str
    ) -> tuple[CustomerProfile, bool]:
        """Provision once from verified identity claims or return the existing profile."""

        candidate = CustomerProfile(
            identity_provider_subject=actor.subject,
            **self._profile_values_from_identity(actor),
        )
        async with self._unit_of_work_factory() as unit:
            profile, provisioned = await unit.customers.provision_profile_if_absent(candidate)
            if not provisioned:
                return profile, False
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "profile.provisioned",
                    "customer_profile",
                    correlation_id,
                    profile.id,
                    {"source": "authenticated_identity"},
                )
            )
            await unit.commit()
            return profile, True

    async def provision_profile(
        self, actor: Principal, values: dict[str, Any], correlation_id: str
    ) -> CustomerProfile:
        async with self._unit_of_work_factory() as unit:
            if await unit.customers.get_profile_by_subject(actor.subject):
                raise ConflictError
            profile = CustomerProfile(identity_provider_subject=actor.subject, **values)
            unit.customers.add_profile(profile)
            await unit.flush()
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "profile.created",
                    "customer_profile",
                    correlation_id,
                    profile.id,
                )
            )
            await unit.commit()
            return profile

    async def get_own_profile(self, actor: Principal) -> CustomerProfile:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_subject(actor.subject)
            if profile is None:
                raise ResourceNotFoundError
            return profile

    async def update_own_profile(
        self, actor: Principal, changes: dict[str, Any], correlation_id: str
    ) -> CustomerProfile:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_subject(actor.subject)
            if profile is None:
                raise ResourceNotFoundError
            self._require_mutable(profile)
            allowed_changes = {key: value for key, value in changes.items() if key != "status"}
            updated = replace(profile, **allowed_changes, updated_at=utc_now())
            await unit.customers.update_profile(updated)
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "profile.updated",
                    "customer_profile",
                    correlation_id,
                    profile.id,
                    {"changed_fields": sorted(allowed_changes)},
                )
            )
            await unit.commit()
            return updated

    async def add_address(
        self, actor: Principal, values: dict[str, Any], correlation_id: str
    ) -> CustomerAddress:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_subject(actor.subject)
            if profile is None:
                raise ResourceNotFoundError
            self._require_mutable(profile)
            existing = await unit.customers.list_addresses(profile.id)
            make_default = bool(values.pop("is_default", False)) or not existing
            if make_default:
                await unit.customers.clear_default_addresses(profile.id)
                await unit.flush()
            address = CustomerAddress(customer_id=profile.id, is_default=make_default, **values)
            unit.customers.add_address(address)
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "address.created",
                    "customer_address",
                    correlation_id,
                    address.id,
                    {"default_selected": make_default},
                )
            )
            await unit.commit()
            return address

    async def list_own_addresses(self, actor: Principal) -> list[CustomerAddress]:
        profile = await self.get_own_profile(actor)
        async with self._unit_of_work_factory() as unit:
            return await unit.customers.list_addresses(profile.id)

    async def update_address(
        self,
        actor: Principal,
        address_id: UUID,
        changes: dict[str, Any],
        correlation_id: str,
    ) -> CustomerAddress:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_subject(actor.subject)
            if profile is None:
                raise ResourceNotFoundError
            self._require_mutable(profile)
            address = await unit.customers.get_address_for_customer(profile.id, address_id)
            if address is None:
                raise ResourceNotFoundError
            updated = replace(address, **changes, updated_at=utc_now())
            await unit.customers.update_address(updated)
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "address.updated",
                    "customer_address",
                    correlation_id,
                    address.id,
                    {"changed_fields": sorted(changes)},
                )
            )
            await unit.commit()
            return updated

    async def select_default_address(
        self, actor: Principal, address_id: UUID, correlation_id: str
    ) -> CustomerAddress:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_subject(actor.subject)
            if profile is None:
                raise ResourceNotFoundError
            self._require_mutable(profile)
            address = await unit.customers.get_address_for_customer(profile.id, address_id)
            if address is None:
                raise ResourceNotFoundError
            await unit.customers.clear_default_addresses(profile.id)
            await unit.flush()
            updated = replace(address, is_default=True, updated_at=utc_now())
            await unit.customers.update_address(updated)
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "address.default_selected",
                    "customer_address",
                    correlation_id,
                    address.id,
                )
            )
            await unit.commit()
            return updated

    async def delete_address(self, actor: Principal, address_id: UUID, correlation_id: str) -> None:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_subject(actor.subject)
            if profile is None:
                raise ResourceNotFoundError
            self._require_mutable(profile)
            address = await unit.customers.get_address_for_customer(profile.id, address_id)
            if address is None:
                raise ResourceNotFoundError
            was_default = address.is_default
            await unit.customers.delete_address(address)
            await unit.flush()
            if was_default:
                remaining = await unit.customers.list_addresses(profile.id)
                if remaining:
                    promoted = replace(remaining[0], is_default=True, updated_at=utc_now())
                    await unit.customers.update_address(promoted)
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "address.deleted",
                    "customer_address",
                    correlation_id,
                    address.id,
                    {"default_was_reassigned": was_default},
                )
            )
            await unit.commit()

    async def get_profile_by_id(self, customer_id: UUID) -> CustomerProfile:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_id(customer_id)
            if profile is None:
                raise ResourceNotFoundError
            return profile

    async def list_profiles(self, offset: int, limit: int) -> list[CustomerProfile]:
        async with self._unit_of_work_factory() as unit:
            return await unit.customers.list_profiles(offset, limit)

    async def change_status(
        self,
        actor: Principal,
        customer_id: UUID,
        status: CustomerStatus,
        reason: AccountStatusReason,
        correlation_id: str,
    ) -> CustomerProfile:
        async with self._unit_of_work_factory() as unit:
            profile = await unit.customers.get_profile_by_id(customer_id)
            if profile is None:
                raise ResourceNotFoundError
            if profile.status is status:
                raise ConflictError
            old_status = profile.status
            updated = replace(profile, status=status, updated_at=utc_now())
            await unit.customers.update_profile(updated)
            unit.customers.add_audit_event(
                self._event(
                    profile.id,
                    actor,
                    "account.status_changed",
                    "customer_profile",
                    correlation_id,
                    profile.id,
                    {
                        "old_status": old_status.value,
                        "new_status": status.value,
                        "reason_code": reason.value,
                    },
                )
            )
            await unit.commit()
            return updated

    async def list_activity(
        self, customer_id: UUID, offset: int, limit: int
    ) -> list[CustomerAuditEvent]:
        async with self._unit_of_work_factory() as unit:
            if await unit.customers.get_profile_by_id(customer_id) is None:
                raise ResourceNotFoundError
            return await unit.customers.list_audit_events(customer_id, offset, limit)

    async def list_own_activity(
        self, actor: Principal, offset: int, limit: int
    ) -> list[CustomerAuditEvent]:
        profile = await self.get_own_profile(actor)
        return await self.list_activity(profile.id, offset, limit)
