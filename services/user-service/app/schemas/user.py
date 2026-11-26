from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.core.constants import UserRole


class InternalUserCreate(BaseModel):
    id: Optional[int] = None
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    role: UserRole = UserRole.CUSTOMER
    is_active: bool = True


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    phone: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
