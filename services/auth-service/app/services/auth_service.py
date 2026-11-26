import logging
from sqlalchemy.orm import Session

from app.clients import user_client
from app.core.constants import UserRole
from app.exceptions import ConflictException, UnauthorizedException
from app.models.auth_credential import AuthCredential
from app.repositories.auth_repository import auth_repository
from app.schemas.auth import UserRegister, UserLogin, UserCreateAdmin, Token, UserResponse
from app.security import get_password_hash, verify_password, create_access_token

logger = logging.getLogger("auth-service.audit")


class AuthService:
    def _create_account(
        self,
        db: Session,
        email: str,
        password: str,
        full_name: str,
        phone: str,
        role: UserRole,
    ) -> UserResponse:
        existing = auth_repository.get_by_email(db, email)
        if existing:
            raise ConflictException(
                f"User with email '{email}' already exists",
                code="EMAIL_ALREADY_EXISTS",
            )

        credential = AuthCredential(
            email=email,
            password_hash=get_password_hash(password),
            role=role,
            is_active=True,
        )
        created_cred = auth_repository.create(db, credential)

        try:
            profile = user_client.create_user_profile(
                {
                    "id": created_cred.id,
                    "email": created_cred.email,
                    "full_name": full_name,
                    "phone": phone,
                    "role": role.value,
                    "is_active": created_cred.is_active,
                }
            )
        except Exception:
            # Compensating transaction: remove credential if user-service profile creation fails
            auth_repository.delete(db, created_cred)
            raise

        logger.info(f"AUDIT: Account created ID={created_cred.id} email={created_cred.email} role={role.value}")
        return UserResponse(**profile)

    def register_customer(self, db: Session, data: UserRegister) -> UserResponse:
        return self._create_account(
            db=db,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone=data.phone,
            role=UserRole.CUSTOMER,
        )

    def admin_create_user(self, db: Session, data: UserCreateAdmin) -> UserResponse:
        return self._create_account(
            db=db,
            email=data.email,
            password=data.password,
            full_name=data.full_name,
            phone=data.phone,
            role=data.role,
        )

    def login(self, db: Session, data: UserLogin) -> Token:
        cred = auth_repository.get_by_email(db, data.email)
        if not cred or not verify_password(data.password, cred.password_hash):
            auth_repository.log_login_attempt(
                db=db,
                email=data.email,
                success=False,
                user_id=cred.id if cred else None,
                reason="INVALID_CREDENTIALS",
            )
            logger.warning(f"AUDIT: Failed login attempt for email {data.email}")
            raise UnauthorizedException("Incorrect email or password", code="INVALID_CREDENTIALS")

        if not cred.is_active:
            auth_repository.log_login_attempt(
                db=db,
                email=data.email,
                success=False,
                user_id=cred.id,
                reason="INACTIVE_USER",
            )
            logger.warning(f"AUDIT: Login attempt on inactive account {cred.id}")
            raise UnauthorizedException("User account is inactive", code="INACTIVE_USER")

        role_value = cred.role.value if hasattr(cred.role, "value") else str(cred.role)
        profile = user_client.get_user(cred.id)
        full_name = profile.get("full_name") if profile else None

        token_data = {
            "sub": str(cred.id),
            "role": role_value,
            "email": cred.email,
            "full_name": full_name,
        }
        access_token = create_access_token(data=token_data)
        auth_repository.log_login_attempt(
            db=db,
            email=cred.email,
            success=True,
            user_id=cred.id,
            reason="SUCCESS",
        )
        logger.info(f"AUDIT: Successful login user ID={cred.id} role={role_value}")
        return Token(
            access_token=access_token,
            token_type="bearer",
            role=cred.role,
            user_id=cred.id,
        )


auth_service = AuthService()
