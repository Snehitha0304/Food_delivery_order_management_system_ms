from fastapi import APIRouter, Depends, Header
from app.exceptions import UnauthorizedException
from app.security import decode_access_token, verify_internal_api_key

router = APIRouter(
    prefix="/internal",
    tags=["Internal Service API"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/auth/verify")
def internal_verify_token(authorization: str = Header(default="")):
    if not authorization.lower().startswith("bearer "):
        raise UnauthorizedException("Missing bearer token", code="AUTHENTICATION_REQUIRED")
    token = authorization.split(" ", 1)[1].strip()
    return decode_access_token(token)
