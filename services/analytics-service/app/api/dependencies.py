"""Authentication, authorization, and dashboard application dependencies."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.application.dashboard import DashboardService
from app.core.errors import (
    AuthenticationError,
    AuthorizationError,
    IdentityProviderUnavailableError,
)
from app.core.security import AuthenticatedActor, Role

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="Keycloak access token")
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


async def get_authenticated_actor(
    request: Request, credentials: BearerCredentials = None
) -> AuthenticatedActor:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise AuthenticationError
    verifier = request.app.state.token_verifier
    if verifier is None:
        raise IdentityProviderUnavailableError
    principal = await verifier.verify(credentials.credentials)
    return AuthenticatedActor(principal=principal, access_token=credentials.credentials)


def require_roles(*roles: Role) -> Callable[..., Awaitable[AuthenticatedActor]]:
    async def authorize(
        actor: Annotated[AuthenticatedActor, Depends(get_authenticated_actor)],
    ) -> AuthenticatedActor:
        if not actor.principal.has_any_role(*roles):
            raise AuthorizationError
        return actor

    return authorize


async def get_dashboard_service(request: Request) -> DashboardService:
    return request.app.state.dashboard_service
