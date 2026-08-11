"""FastAPI composition and catalogue authorization dependencies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.catalogue import CatalogueService
from app.core.errors import AuthenticationError, AuthorizationError, DependencyUnavailableError
from app.core.security import Principal, Role

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Keycloak access token")
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_current_principal(
    request: Request, credentials: BearerCredentials = None
) -> Principal:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationError
    verifier = request.app.state.token_verifier
    if verifier is None:
        raise DependencyUnavailableError
    return await verifier.verify(credentials.credentials)


def require_roles(*roles: Role) -> Callable[..., Awaitable[Principal]]:
    async def authorize(
        principal: Annotated[Principal, Depends(get_current_principal)],
    ) -> Principal:
        if not principal.has_any_role(*roles):
            raise AuthorizationError
        return principal

    return authorize


async def get_catalogue_service(request: Request) -> CatalogueService:
    factory = request.app.state.unit_of_work_factory
    if factory is None:
        raise DependencyUnavailableError
    return CatalogueService(factory, request.app.state.settings.supported_currencies)
