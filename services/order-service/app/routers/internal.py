from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus
from app.core.database import get_db
from app.core.pagination import PageParams, PaginatedResponse
from app.schemas.order import (
    OrderResponse,
    InternalOrderSummary,
    InternalAssignAgentRequest,
    InternalTransitionRequest,
    SalesStatsResponse,
    AgentOrderStatsResponse,
    CancellationStatsResponse,
)
from app.security import verify_internal_api_key
from app.services.order_service import order_service

router = APIRouter(
    prefix="/internal",
    tags=["Internal Service API"],
    dependencies=[Depends(verify_internal_api_key)],
)


@router.get("/orders/stats/sales", response_model=SalesStatsResponse)
def internal_sales_stats(
    restaurant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    return order_service.get_sales_stats(db, restaurant_id)


@router.get("/orders/stats/agents", response_model=List[AgentOrderStatsResponse])
def internal_agent_stats(db: Session = Depends(get_db)):
    return order_service.get_agent_order_stats(db)


@router.get("/orders/stats/cancellation-rate", response_model=CancellationStatsResponse)
def internal_cancellation_stats(db: Session = Depends(get_db)):
    return order_service.get_cancellation_stats(db)


@router.get("/orders/by-agent/{agent_id}", response_model=PaginatedResponse[OrderResponse])
def internal_orders_by_agent(
    agent_id: int,
    status: Optional[OrderStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    params = PageParams(page=page, size=size)
    return order_service.internal_get_agent_orders(db, agent_id, status=status, params=params)


@router.get("/orders/{order_id}", response_model=InternalOrderSummary)
def internal_get_order(order_id: int, db: Session = Depends(get_db)):
    return order_service.get_internal_order(db, order_id)


@router.patch("/orders/{order_id}/assign-agent", response_model=OrderResponse)
def internal_assign_agent(
    order_id: int,
    data: InternalAssignAgentRequest,
    db: Session = Depends(get_db),
):
    return order_service.internal_assign_agent(db, order_id, data.agent_id, data.assigned_by)


@router.patch("/orders/{order_id}/transition", response_model=OrderResponse)
def internal_transition_order(
    order_id: int,
    data: InternalTransitionRequest,
    db: Session = Depends(get_db),
):
    return order_service.internal_transition(
        db=db,
        order_id=order_id,
        to_status=data.to_status,
        actor_id=data.actor_id,
        actor_role=data.actor_role,
        remark=data.remark,
    )
