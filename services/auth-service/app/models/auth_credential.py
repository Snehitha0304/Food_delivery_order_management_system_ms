from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SQLEnum
from app.core.database import Base
from app.core.constants import UserRole
from app.models.base import TimestampMixin, utc_now


class AuthCredential(Base, TimestampMixin):
    __tablename__ = "auth_credentials"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    is_active = Column(Boolean, default=True, nullable=False)


class LoginAuditLog(Base):
    __tablename__ = "login_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    email = Column(String(255), nullable=False, index=True)
    success = Column(Boolean, nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
