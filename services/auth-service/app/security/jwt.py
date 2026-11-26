import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.constants import UserRole
from app.exceptions import UnauthorizedException

logger = logging.getLogger("auth-service.security")


class AuthenticatedUser(BaseModel):
    id: int
    role: UserRole
    email: Optional[str] = None
    full_name: Optional[str] = None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    now_utc = datetime.now(timezone.utc)
    expire = now_utc + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": now_utc})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        logger.warning(f"JWT verification failed: {exc}")
        raise UnauthorizedException("Invalid token or token expired", code="INVALID_TOKEN")
