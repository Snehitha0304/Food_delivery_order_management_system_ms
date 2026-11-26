import logging
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.constants import UserRole
from app.exceptions import UnauthorizedException

logger = logging.getLogger("restaurant-service.security")


class AuthenticatedUser(BaseModel):
    id: int
    role: UserRole
    email: Optional[str] = None
    full_name: Optional[str] = None


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        logger.warning(f"JWT verification failed: {exc}")
        raise UnauthorizedException("Invalid token or token expired", code="INVALID_TOKEN")
