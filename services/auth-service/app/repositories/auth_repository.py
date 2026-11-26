from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.auth_credential import AuthCredential, LoginAuditLog


class AuthRepository:
    def get_by_id(self, db: Session, user_id: int) -> Optional[AuthCredential]:
        return db.get(AuthCredential, user_id)

    def get_by_email(self, db: Session, email: str) -> Optional[AuthCredential]:
        stmt = select(AuthCredential).where(AuthCredential.email == email)
        return db.execute(stmt).scalars().first()

    def create(self, db: Session, credential: AuthCredential) -> AuthCredential:
        db.add(credential)
        db.commit()
        db.refresh(credential)
        return credential

    def delete(self, db: Session, credential: AuthCredential) -> None:
        db.delete(credential)
        db.commit()

    def log_login_attempt(
        self,
        db: Session,
        email: str,
        success: bool,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
    ) -> LoginAuditLog:
        entry = LoginAuditLog(user_id=user_id, email=email, success=success, reason=reason)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry


auth_repository = AuthRepository()
