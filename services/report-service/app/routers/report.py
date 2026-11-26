from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.constants import UserRole
from app.core.database import get_db
from app.schemas.report import (
    SalesReportResponse,
    AgentPerformanceResponse,
    CancellationRateResponse,
)
from app.security import AuthenticatedUser, require_role
from app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/restaurant-sales", response_model=SalesReportResponse)
def get_restaurant_sales(
    restaurant_id: Optional[int] = Query(None, description="Restaurant ID (Admin only)"),
    current_user: AuthenticatedUser = Depends(require_role(UserRole.RESTAURANT_OWNER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return report_service.get_sales_report(db, current_user, restaurant_id)


@router.get("/agent-performance", response_model=List[AgentPerformanceResponse])
def get_agent_performance(
    admin: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return report_service.get_agent_performance_report(db, admin)


@router.get("/cancellation-rate", response_model=CancellationRateResponse)
def get_cancellation_rate(
    admin: AuthenticatedUser = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    return report_service.get_cancellation_rate_report(db, admin)
