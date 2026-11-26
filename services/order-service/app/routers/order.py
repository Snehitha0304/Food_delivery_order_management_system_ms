from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus
from app.core.database import get_db
from app.core.pagination import PageParams, PaginatedResponse
from app.schemas.order import OrderCreate, OrderStatusUpdate, OrderResponse, OrderDetailResponse
from app.security import AuthenticatedUser, get_current_user, get_current_customer, get_current_owner
from app.services.order_service import order_service

router = APIRouter(prefix="/orders", tags=["Orders"])


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def place_order(
    data: OrderCreate,
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return order_service.create_order(db, customer.id, data)


@router.get("/me", response_model=PaginatedResponse[OrderResponse])
def get_my_orders(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    params = PageParams(page=page, size=size)
    return order_service.get_customer_orders(db, customer.id, params)


@router.get("/restaurant", response_model=PaginatedResponse[OrderResponse])
def get_restaurant_orders(
    status: Optional[OrderStatus] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    params = PageParams(page=page, size=size)
    return order_service.restaurant_get_orders(db, owner.id, status=status, params=params)


@router.get("/{id}", response_model=OrderDetailResponse)
def get_order_detail(
    id: int,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return order_service.get_order_detail(db, current_user, id)


@router.patch("/{id}/cancel", response_model=OrderResponse)
def cancel_order(
    id: int,
    customer: AuthenticatedUser = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    return order_service.cancel_order(db, customer.id, id)


@router.patch("/{id}/status", response_model=OrderResponse)
def update_order_status(
    id: int,
    data: OrderStatusUpdate,
    owner: AuthenticatedUser = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    return order_service.restaurant_update_status(db, owner.id, id, data.status, data.remark)
