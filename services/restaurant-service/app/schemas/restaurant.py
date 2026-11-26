from datetime import datetime, time
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class RestaurantBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    cuisine: str = Field(..., min_length=2, max_length=100)
    city: str = Field(..., min_length=2, max_length=100)
    address: str = Field(..., min_length=5, max_length=255)
    opens_at: time
    closes_at: time
    is_open: bool = True


class RestaurantCreate(RestaurantBase):
    pass


class RestaurantUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    cuisine: Optional[str] = Field(None, min_length=2, max_length=100)
    city: Optional[str] = Field(None, min_length=2, max_length=100)
    address: Optional[str] = Field(None, min_length=5, max_length=255)
    opens_at: Optional[time] = None
    closes_at: Optional[time] = None
    is_open: Optional[bool] = None


class RestaurantOpenStatusUpdate(BaseModel):
    is_open: bool


class RestaurantRatingUpdate(BaseModel):
    avg_rating: Decimal = Field(..., ge=0, le=5)


class RestaurantResponse(RestaurantBase):
    id: int
    owner_id: int
    avg_rating: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
