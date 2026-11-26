from typing import Optional
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer

from app.core.config import settings
from app.core.constants import UserRole
from app.exceptions import UnauthorizedException, ForbiddenException
from app.security.jwt import AuthenticatedUser, decode_access_token

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> AuthenticatedUser:
    if not token:
        raise UnauthorizedException("Authentication credentials were not provided", code="AUTHENTICATION_REQUIRED")

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    role_raw = payload.get("role")
    if user_id is None or role_raw is None:
        raise UnauthorizedException("Invalid token payload", code="INVALID_TOKEN")

    try:
        return AuthenticatedUser(
            id=int(user_id),
            role=UserRole(role_raw),
            email=payload.get("email"),
            full_name=payload.get("full_name"),
        )
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid user claims in token", code="INVALID_TOKEN")


def require_role(*allowed_roles: UserRole):
    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        allowed_values = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if current_user.role.value not in allowed_values:
            raise ForbiddenException(
                detail=f"Operation requires one of the following roles: {', '.join(allowed_values)}",
                code="ROLE_NOT_AUTHORIZED",
            )
        return current_user

    return role_checker


get_current_admin = require_role(UserRole.ADMIN)


def verify_internal_api_key(x_internal_api_key: Optional[str] = Header(default=None)) -> None:
    if not x_internal_api_key or x_internal_api_key != settings.INTERNAL_API_KEY:
        raise UnauthorizedException("Invalid or missing internal service API key", code="INVALID_INTERNAL_API_KEY")
