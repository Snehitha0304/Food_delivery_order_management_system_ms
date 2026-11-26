from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus
from app.core.database import get_db
from app.schemas.delivery import (
    OrderAgentAssign,
    OrderDeliveryStatusUpdate,
    OrderResponse,
    PaginatedOrderResponse,
)
from app.security import AuthenticatedUser, get_current_admin, get_current_agent
from app.services.delivery_service import delivery_service

router = APIRouter(tags=["Delivery"])


@router.patch("/orders/{id}/assign-agent", response_model=OrderResponse)
def assign_delivery_agent(
    id: int,
    data: OrderAgentAssign,
    admin: AuthenticatedUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return delivery_service.admin_assign_agent(db, admin.id, id, data.agent_id)


@router.get("/orders/agent", response_model=PaginatedOrderResponse)
def get_agent_orders(
    status: Optional[OrderStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    agent: AuthenticatedUser = Depends(get_current_agent),
):
    return delivery_service.get_agent_orders(agent.id, status=status, page=page, size=size)


@router.patch("/orders/{id}/delivery-status", response_model=OrderResponse)
def update_delivery_status(
    id: int,
    data: OrderDeliveryStatusUpdate,
    agent: AuthenticatedUser = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    return delivery_service.agent_update_delivery_status(db, agent.id, id, data.status, data.remark)
