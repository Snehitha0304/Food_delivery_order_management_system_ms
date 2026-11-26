from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    display_order: int = Field(default=0, ge=0)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    display_order: Optional[int] = Field(None, ge=0)


class CategoryResponse(CategoryBase):
    id: int
    restaurant_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MenuItemBase(BaseModel):
    category_id: int
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    price: Decimal = Field(..., gt=0, decimal_places=2)
    is_veg: bool = True
    is_available: bool = True


class MenuItemCreate(MenuItemBase):
    pass


class MenuItemUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    is_veg: Optional[bool] = None
    is_available: Optional[bool] = None


class MenuItemAvailabilityUpdate(BaseModel):
    is_available: bool


class MenuItemBatchRequest(BaseModel):
    item_ids: List[int] = Field(..., min_length=1)


class MenuItemResponse(MenuItemBase):
    id: int
    restaurant_id: int
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CategoryWithItems(BaseModel):
    id: int
    name: str
    display_order: int
    items: List[MenuItemResponse]


class RestaurantMenuResponse(BaseModel):
    restaurant_id: int
    restaurant_name: str
    categories: List[CategoryWithItems]
