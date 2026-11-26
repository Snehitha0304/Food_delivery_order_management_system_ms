from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class SalesReportResponse(BaseModel):
    restaurant_id: Optional[int] = None
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    total_revenue: Decimal
    avg_order_value: Decimal


class AgentPerformanceResponse(BaseModel):
    agent_id: int
    agent_name: str
    total_assigned: int
    total_delivered: int
    avg_rating: Optional[Decimal] = None


class CancellationRateResponse(BaseModel):
    total_orders: int
    cancelled_orders: int
    rejected_orders: int
    cancellation_rate_percentage: Decimal
