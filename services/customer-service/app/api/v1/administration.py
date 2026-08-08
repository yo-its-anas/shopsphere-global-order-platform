"""Least-privilege customer support and operations routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from app.api.dependencies import get_customer_service, require_roles
from app.api.v1.customers import _audit_response, _profile_response
from app.application.customer_accounts import CustomerAccountService
from app.core.security import Principal, Role
from app.schemas.customer import (
    AccountStatusUpdate,
    AuditEventListResponse,
    ProfileListResponse,
    ProfileResponse,
)

router = APIRouter(prefix="/admin/customers", tags=["Customer administration"])
support_or_operations = require_roles(Role.SUPPORT, Role.OPERATIONS_ADMIN)
operations_only = require_roles(Role.OPERATIONS_ADMIN)
SupportActor = Annotated[Principal, Depends(support_or_operations)]
OperationsActor = Annotated[Principal, Depends(operations_only)]
CustomerService = Annotated[CustomerAccountService, Depends(get_customer_service)]


@router.get("", response_model=ProfileListResponse, summary="List customer profiles")
async def list_profiles(
    _: SupportActor,
    service: CustomerService,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ProfileListResponse:
    profiles = await service.list_profiles(offset, limit)
    return ProfileListResponse(
        items=[_profile_response(item) for item in profiles],
        offset=offset,
        limit=limit,
    )


@router.get(
    "/{customer_id}",
    response_model=ProfileResponse,
    summary="Retrieve a customer profile for authorized support",
)
async def get_profile(
    customer_id: UUID,
    _: SupportActor,
    service: CustomerService,
) -> ProfileResponse:
    profile = await service.get_profile_by_id(customer_id)
    return _profile_response(profile)


@router.get(
    "/{customer_id}/activity",
    response_model=AuditEventListResponse,
    summary="Retrieve customer-domain activity for authorized support",
)
async def list_activity(
    customer_id: UUID,
    _: SupportActor,
    service: CustomerService,
    offset: Annotated[int, Query(ge=0, le=100_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> AuditEventListResponse:
    events = await service.list_activity(customer_id, offset, limit)
    return AuditEventListResponse(
        items=[_audit_response(item) for item in events],
        offset=offset,
        limit=limit,
    )


@router.patch(
    "/{customer_id}/status",
    response_model=ProfileResponse,
    summary="Change customer account status as an operations administrator",
)
async def change_status(
    customer_id: UUID,
    payload: AccountStatusUpdate,
    request: Request,
    actor: OperationsActor,
    service: CustomerService,
) -> ProfileResponse:
    profile = await service.change_status(
        actor,
        customer_id,
        payload.status,
        payload.reason_code,
        str(request.state.correlation_id),
    )
    return _profile_response(profile)
