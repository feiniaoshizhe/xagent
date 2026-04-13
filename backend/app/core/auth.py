"""Minimal auth bridge for step 1 backend APIs."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header

from app.core.errors import ApiError
from app.common.settings import settings


@dataclass(slots=True)
class AuthenticatedUser:
    """Authenticated user context."""

    user_id: str
    role: str

    @property
    def is_admin(self) -> bool:
        """Return whether the current user is an administrator."""

        return self.role == "admin"


async def require_authenticated_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
    x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
) -> AuthenticatedUser:
    """Resolve the current user from a minimal bridge."""

    if authorization and settings.internal_api_key:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() == "bearer" and token == settings.internal_api_key:
            return AuthenticatedUser(user_id="internal", role="admin")

    if x_user_id:
        return AuthenticatedUser(user_id=x_user_id, role=x_user_role or "user")

    if settings.allow_insecure_dev_auth and settings.environment != "prod":
        return AuthenticatedUser(
            user_id=settings.default_admin_user_id,
            role=settings.default_admin_role,
        )

    raise ApiError(
        401,
        "Authentication required",
        error="Unauthorized",
        data={
            "why": "No authenticated user context was provided.",
            "fix": "Forward bridge headers or configure backend auth integration.",
        },
    )


async def require_admin(
    user: Annotated[AuthenticatedUser, Depends(require_authenticated_user)],
) -> AuthenticatedUser:
    """Ensure the current user is an administrator."""

    if not user.is_admin:
        raise ApiError(
            403,
            "Admin access required",
            error="Forbidden",
            data={
                "why": "This endpoint requires the admin role.",
                "fix": "Sign in as an administrator before retrying.",
            },
        )
    return user
