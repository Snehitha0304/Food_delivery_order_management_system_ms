from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from app.clients import user_client, restaurant_client, order_client, rating_client
from app.core.constants import UserRole
from app.exceptions import ForbiddenException
from app.repositories.report_repository import report_repository
from app.schemas.report import (
    SalesReportResponse,
    AgentPerformanceResponse,
    CancellationRateResponse,
)
from app.security import AuthenticatedUser


class ReportService:
    def get_sales_report(
        self,
        db: Session,
        current_user: AuthenticatedUser,
        restaurant_id: Optional[int] = None,
    ) -> SalesReportResponse:
        if current_user.role == UserRole.RESTAURANT_OWNER:
            restaurant = restaurant_client.get_restaurant_by_owner(current_user.id)
            if not restaurant:
                raise ForbiddenException("You do not have a registered restaurant", code="RESTAURANT_NOT_FOUND")
            target_restaurant_id = restaurant["id"]
        elif current_user.role == UserRole.ADMIN:
            target_restaurant_id = restaurant_id
        else:
            raise ForbiddenException("Access denied to sales reports", code="REPORT_ACCESS_FORBIDDEN")

        data = order_client.get_sales_stats(target_restaurant_id)
        response = SalesReportResponse(**data)
        report_repository.save_snapshot(
            db=db,
            report_type="restaurant_sales",
            requested_by=current_user.id,
            requested_role=current_user.role.value,
            payload=response.model_dump(mode="json"),
            filter_context=f"restaurant_id={target_restaurant_id}",
        )
        return response

    def get_agent_performance_report(
        self,
        db: Session,
        admin: AuthenticatedUser,
    ) -> List[AgentPerformanceResponse]:
        agents = user_client.list_delivery_agents()
        order_stats = {row["agent_id"]: row for row in order_client.get_agent_stats()}
        rating_stats = {row["agent_id"]: row["avg_rating"] for row in rating_client.get_agent_averages()}

        results: List[AgentPerformanceResponse] = []
        for agent in agents:
            aid = agent["id"]
            stats = order_stats.get(aid, {})
            avg_val = rating_stats.get(aid)
            results.append(
                AgentPerformanceResponse(
                    agent_id=aid,
                    agent_name=agent["full_name"],
                    total_assigned=stats.get("total_assigned", 0),
                    total_delivered=stats.get("total_delivered", 0),
                    avg_rating=Decimal(str(avg_val)) if avg_val is not None else None,
                )
            )

        report_repository.save_snapshot(
            db=db,
            report_type="agent_performance",
            requested_by=admin.id,
            requested_role=admin.role.value,
            payload=[r.model_dump(mode="json") for r in results],
        )
        return results

    def get_cancellation_rate_report(
        self,
        db: Session,
        admin: AuthenticatedUser,
    ) -> CancellationRateResponse:
        data = order_client.get_cancellation_stats()
        response = CancellationRateResponse(**data)
        report_repository.save_snapshot(
            db=db,
            report_type="cancellation_rate",
            requested_by=admin.id,
            requested_role=admin.role.value,
            payload=response.model_dump(mode="json"),
        )
        return response


report_service = ReportService()
