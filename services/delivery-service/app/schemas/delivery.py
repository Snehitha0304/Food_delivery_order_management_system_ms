from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.core.constants import OrderStatus


class OrderAgentAssign(BaseModel):
    agent_id: int


class OrderDeliveryStatusUpdate(BaseModel):
    status: OrderStatus
    remark: Optional[str] = None


class OrderResponse(BaseModel):
    id: int
    order_no: str
    customer_id: int
    restaurant_id: int
    address_id: int
    agent_id: Optional[int]
    status: OrderStatus
    item_total: Decimal
    tax_amount: Decimal
    delivery_fee: Decimal
    grand_total: Decimal
    placed_at: datetime
    delivered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class PaginatedOrderResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    page: int
    size: int
    total_pages: int


class DeliveryRecordResponse(BaseModel):
    id: int
    order_id: int
    agent_id: int
    assigned_by: int
    status: str
    assigned_at: datetime
    picked_up_at: Optional[datetime]
    delivered_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)
