from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.core.constants import OrderStatus, UserRole


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., ge=1)
    price: Optional[Decimal] = Field(None, description="Client-supplied price, ignored by server")


class OrderCreate(BaseModel):
    restaurant_id: int
    address_id: int
    items: List[OrderItemCreate] = Field(..., min_length=1)


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    remark: Optional[str] = None


class OrderItemResponse(BaseModel):
    id: int
    menu_item_id: int
    item_name_snapshot: str
    unit_price_snapshot: Decimal
    quantity: int
    line_total: Decimal

    model_config = ConfigDict(from_attributes=True)


class OrderStatusHistoryResponse(BaseModel):
    id: int
    order_id: int
    from_status: Optional[str]
    to_status: str
    changed_by: int
    changed_at: datetime
    remark: Optional[str]

    model_config = ConfigDict(from_attributes=True)


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

    model_config = ConfigDict(from_attributes=True)


class OrderDetailResponse(OrderResponse):
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    items: List[OrderItemResponse] = []
    status_history: List[OrderStatusHistoryResponse] = []


class InternalOrderSummary(OrderResponse):
    restaurant_owner_id: int


class InternalAssignAgentRequest(BaseModel):
    agent_id: int
    assigned_by: int


class InternalTransitionRequest(BaseModel):
    to_status: OrderStatus
    actor_id: int
    actor_role: UserRole
    remark: Optional[str] = None


class SalesStatsResponse(BaseModel):
    restaurant_id: Optional[int] = None
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: Decimal
    avg_order_value: Decimal


class AgentOrderStatsResponse(BaseModel):
    agent_id: int
    total_assigned: int
    total_delivered: int


class CancellationStatsResponse(BaseModel):
    total_orders: int
    cancelled_orders: int
    rejected_orders: int
    cancellation_rate_percentage: Decimal
