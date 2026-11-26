import logging
from typing import Optional
from fastapi import Depends, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import UserRole
from app.core.database import get_db
from app.exceptions import UnauthorizedException, ForbiddenException
from app.models.auth_credential import AuthCredential
from app.security.jwt import AuthenticatedUser, decode_access_token

logger = logging.getLogger("auth-service.audit")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login",
    auto_error=False,
)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> AuthenticatedUser:
    if not token:
        raise UnauthorizedException(
            "Authentication credentials were not provided",
            code="AUTHENTICATION_REQUIRED",
        )

    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedException("Invalid token payload", code="INVALID_TOKEN")

    try:
        user_id_int = int(user_id)
    except (ValueError, TypeError):
        raise UnauthorizedException("Invalid user id in token", code="INVALID_TOKEN")

    cred = db.query(AuthCredential).filter(AuthCredential.id == user_id_int).first()
    if not cred:
        raise UnauthorizedException("User not found", code="USER_NOT_FOUND")
    if not cred.is_active:
        raise ForbiddenException("User account is inactive", code="INACTIVE_USER")

    return AuthenticatedUser(
        id=cred.id,
        role=cred.role,
        email=cred.email,
        full_name=payload.get("full_name"),
    )


def require_role(*allowed_roles: UserRole):
    def role_checker(current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        allowed_values = [r.value if hasattr(r, "value") else str(r) for r in allowed_roles]
        if current_user.role.value not in allowed_values:
            logger.warning(f"Access denied for user {current_user.id} ({current_user.role.value}). Allowed: {allowed_values}")
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
