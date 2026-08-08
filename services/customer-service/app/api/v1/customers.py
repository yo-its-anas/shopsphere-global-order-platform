"""Authenticated customer self-service routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.api.dependencies import get_customer_service, require_roles
from app.application.customer_accounts import CustomerAccountService
from app.core.security import Principal, Role
from app.domain.models import CustomerAddress, CustomerAuditEvent, CustomerProfile
from app.schemas.customer import (
    AddressCreate,
    AddressResponse,
    AddressUpdate,
    AuditEventListResponse,
    AuditEventResponse,
    ProfileCreate,
    ProfileProvisioningResponse,
    ProfileResponse,
    ProfileUpdate,
)

router = APIRouter(prefix="/customers/me", tags=["Customer self-service"])
customer_actor = require_roles(Role.CUSTOMER)
CustomerActor = Annotated[Principal, Depends(customer_actor)]
CustomerService = Annotated[CustomerAccountService, Depends(get_customer_service)]


def _request_id(request: Request) -> str:
    return str(request.state.correlation_id)


def _profile_response(profile: CustomerProfile) -> ProfileResponse:
    return ProfileResponse(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        email=profile.email,
        phone=profile.phone,
        status=profile.status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
    )


def _address_response(address: CustomerAddress) -> AddressResponse:
    return AddressResponse(
        id=address.id,
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


def _audit_response(event: CustomerAuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        customer_id=event.customer_id,
        actor_subject=event.actor_subject,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        occurred_at=event.occurred_at,
        correlation_id=event.correlation_id,
        metadata=event.safe_metadata,
    )


@router.put(
    "",
    response_model=ProfileProvisioningResponse,
    summary="Provision or reuse the profile for the authenticated identity",
)
async def provision_authenticated_profile(
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> ProfileProvisioningResponse:
    profile, provisioned = await service.provision_authenticated_profile(
        actor, _request_id(request)
    )
    return ProfileProvisioningResponse(
        profile=_profile_response(profile),
        provisioned=provisioned,
    )


@router.post(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Provision the current customer's profile",
)
async def provision_profile(
    payload: ProfileCreate,
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> ProfileResponse:
    profile = await service.provision_profile(actor, payload.model_dump(), _request_id(request))
    return _profile_response(profile)


@router.get("", response_model=ProfileResponse, summary="Retrieve the current profile")
async def get_profile(
    actor: CustomerActor,
    service: CustomerService,
) -> ProfileResponse:
    return _profile_response(await service.get_own_profile(actor))


@router.patch("", response_model=ProfileResponse, summary="Update allowed profile fields")
async def update_profile(
    payload: ProfileUpdate,
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> ProfileResponse:
    profile = await service.update_own_profile(
        actor,
        payload.model_dump(exclude_unset=True),
        _request_id(request),
    )
    return _profile_response(profile)


@router.post(
    "/addresses",
    response_model=AddressResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an address owned by the current customer",
)
async def add_address(
    payload: AddressCreate,
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> AddressResponse:
    address = await service.add_address(actor, payload.model_dump(), _request_id(request))
    return _address_response(address)


@router.get(
    "/addresses",
    response_model=list[AddressResponse],
    summary="List addresses owned by the current customer",
)
async def list_addresses(
    actor: CustomerActor,
    service: CustomerService,
) -> list[AddressResponse]:
    addresses = await service.list_own_addresses(actor)
    return [_address_response(item) for item in addresses]


@router.patch(
    "/addresses/{address_id}",
    response_model=AddressResponse,
    summary="Update an address owned by the current customer",
)
async def update_address(
    address_id: UUID,
    payload: AddressUpdate,
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> AddressResponse:
    address = await service.update_address(
        actor,
        address_id,
        payload.model_dump(exclude_unset=True),
        _request_id(request),
    )
    return _address_response(address)


@router.put(
    "/addresses/{address_id}/default",
    response_model=AddressResponse,
    summary="Select the current customer's default address",
)
async def select_default_address(
    address_id: UUID,
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> AddressResponse:
    address = await service.select_default_address(actor, address_id, _request_id(request))
    return _address_response(address)


@router.delete(
    "/addresses/{address_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an address owned by the current customer",
)
async def delete_address(
    address_id: UUID,
    request: Request,
    actor: CustomerActor,
    service: CustomerService,
) -> Response:
    await service.delete_address(actor, address_id, _request_id(request))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/activity",
    response_model=AuditEventListResponse,
    summary="List the current customer's domain activity",
)
async def list_activity(
    actor: CustomerActor,
    service: CustomerService,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AuditEventListResponse:
    events = await service.list_own_activity(actor, offset, limit)
    return AuditEventListResponse(
        items=[_audit_response(item) for item in events],
        offset=offset,
        limit=limit,
    )
