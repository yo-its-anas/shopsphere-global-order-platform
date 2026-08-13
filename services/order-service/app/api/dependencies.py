"""Authentication and cart application dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.cart import CartService
from app.application.checkout import CheckoutService
from app.core.errors import AuthenticationError, AuthorizationError, DependencyUnavailableError
from app.core.security import AuthenticatedActor, Role

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Keycloak access token")
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_customer_actor(
    request: Request, credentials: BearerCredentials = None
) -> AuthenticatedActor:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationError
    verifier = request.app.state.token_verifier
    if verifier is None:
        raise DependencyUnavailableError
    principal = await verifier.verify(credentials.credentials)
    if not principal.has_role(Role.CUSTOMER):
        raise AuthorizationError
    return AuthenticatedActor(principal=principal, access_token=credentials.credentials)


async def get_cart_service(request: Request) -> CartService:
    if request.app.state.unit_of_work_factory is None or request.app.state.catalogue_client is None:
        raise DependencyUnavailableError
    settings = request.app.state.settings
    return CartService(
        request.app.state.unit_of_work_factory,
        request.app.state.catalogue_client,
        settings.cart_currency_code,
        settings.cart_max_item_quantity,
    )


async def get_checkout_service(request: Request) -> CheckoutService:
    if request.app.state.unit_of_work_factory is None or request.app.state.catalogue_client is None:
        raise DependencyUnavailableError
    settings = request.app.state.settings
    return CheckoutService(
        request.app.state.unit_of_work_factory,
        request.app.state.catalogue_client,
        settings.cart_currency_code,
    )
