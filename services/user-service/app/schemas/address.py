from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class AddressBase(BaseModel):
    line1: str = Field(..., min_length=3, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., min_length=2, max_length=100)
    pincode: str = Field(..., pattern=r"^[1-9][0-9]{5}$")
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    line1: Optional[str] = Field(None, min_length=3, max_length=255)
    line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    pincode: Optional[str] = Field(None, pattern=r"^[1-9][0-9]{5}$")
    is_default: Optional[bool] = None


class AddressResponse(AddressBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
