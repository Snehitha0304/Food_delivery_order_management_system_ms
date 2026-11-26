from fastapi import APIRouter, Depends, Request, status
from fastapi.concurrency import run_in_threadpool
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.exceptions import BadRequestException, ValidationException
from app.schemas.auth import UserRegister, UserLogin, UserCreateAdmin, Token, UserResponse
from app.security import AuthenticatedUser, get_current_admin
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register as customer",
)
def register_customer(data: UserRegister, db: Session = Depends(get_db)):
    return auth_service.register_customer(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Log in with email/password (supports JSON body and OAuth2 form)",
)
async def login(request: Request, db: Session = Depends(get_db)):
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise BadRequestException("Missing login credentials", code="CREDENTIALS_MISSING")

    try:
        login_dto = UserLogin(email=email, password=password)
    except ValidationError as exc:
        raise ValidationException(str(exc), code="SCHEMA_VALIDATION_ERROR")

    return await run_in_threadpool(auth_service.login, db, login_dto)


@router.post(
    "/admin/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin onboarding for Restaurant Owner, Delivery Agent, or Admin",
)
def admin_create_user(
    data: UserCreateAdmin,
    admin: AuthenticatedUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return auth_service.admin_create_user(db, data)
