from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.order_status_history import OrderStatusHistory


class OrderRepository:
    def create(self, db: Session, order: Order, items: List[OrderItem], user_id: int) -> Order:
        db.add(order)
        db.flush()

        for item in items:
            item.order_id = order.id
            db.add(item)

        initial_history = OrderStatusHistory(
            order_id=order.id,
            from_status=None,
            to_status=OrderStatus.PLACED.value,
            changed_by=user_id,
            changed_at=datetime.now(timezone.utc),
            remark="Order placed successfully",
        )
        db.add(initial_history)

        db.commit()
        db.refresh(order)
        return order

    def get_by_id(self, db: Session, order_id: int) -> Optional[Order]:
        return db.get(Order, order_id)

    def get_by_order_no(self, db: Session, order_no: str) -> Optional[Order]:
        stmt = select(Order).where(Order.order_no == order_no)
        return db.execute(stmt).scalars().first()

    def get_by_customer_id(
        self,
        db: Session,
        customer_id: int,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Order], int]:
        count_stmt = select(func.count(Order.id)).where(Order.customer_id == customer_id)
        stmt = (
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(Order.placed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        total = db.execute(count_stmt).scalar() or 0
        items = list(db.execute(stmt).scalars().all())
        return items, total

    def get_by_restaurant_id(
        self,
        db: Session,
        restaurant_id: int,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Order], int]:
        stmt = select(Order).where(Order.restaurant_id == restaurant_id)
        count_stmt = select(func.count(Order.id)).where(Order.restaurant_id == restaurant_id)

        if status:
            stmt = stmt.where(Order.status == status)
            count_stmt = count_stmt.where(Order.status == status)

        total = db.execute(count_stmt).scalar() or 0
        items = list(db.execute(stmt.order_by(Order.placed_at.desc()).offset(skip).limit(limit)).scalars().all())
        return items, total

    def get_by_agent_id(
        self,
        db: Session,
        agent_id: int,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Order], int]:
        stmt = select(Order).where(Order.agent_id == agent_id)
        count_stmt = select(func.count(Order.id)).where(Order.agent_id == agent_id)

        if status:
            stmt = stmt.where(Order.status == status)
            count_stmt = count_stmt.where(Order.status == status)

        total = db.execute(count_stmt).scalar() or 0
        items = list(db.execute(stmt.order_by(Order.placed_at.desc()).offset(skip).limit(limit)).scalars().all())
        return items, total

    def record_transition(
        self,
        db: Session,
        order: Order,
        to_status: OrderStatus,
        user_id: int,
        remark: Optional[str] = None,
    ) -> Order:
        from_status = order.status.value if hasattr(order.status, "value") else str(order.status)
        order.status = to_status
        now_utc = datetime.now(timezone.utc)

        if to_status == OrderStatus.DELIVERED:
            order.delivered_at = now_utc

        history = OrderStatusHistory(
            order_id=order.id,
            from_status=from_status,
            to_status=to_status.value,
            changed_by=user_id,
            changed_at=now_utc,
            remark=remark,
        )
        db.add(history)
        db.commit()
        db.refresh(order)
        return order

    def assign_agent(self, db: Session, order: Order, agent_id: int, user_id: int) -> Order:
        order.agent_id = agent_id
        history = OrderStatusHistory(
            order_id=order.id,
            from_status=order.status.value,
            to_status=order.status.value,
            changed_by=user_id,
            changed_at=datetime.now(timezone.utc),
            remark=f"Delivery agent assigned: ID {agent_id}",
        )
        db.add(history)
        db.commit()
        db.refresh(order)
        return order

    def get_sales_stats(self, db: Session, restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        delivered_revenue = case((Order.status == OrderStatus.DELIVERED, Order.grand_total), else_=0)
        delivered_count = case((Order.status == OrderStatus.DELIVERED, 1), else_=0)
        cancelled_count = case((Order.status.in_([OrderStatus.CANCELLED, OrderStatus.REJECTED]), 1), else_=0)

        stmt = select(
            func.count(Order.id).label("total_orders"),
            func.coalesce(func.sum(delivered_revenue), 0).label("total_revenue"),
            func.coalesce(func.sum(delivered_count), 0).label("completed_orders"),
            func.coalesce(func.sum(cancelled_count), 0).label("cancelled_orders"),
        )
        if restaurant_id is not None:
            stmt = stmt.where(Order.restaurant_id == restaurant_id)

        row = db.execute(stmt).first()
        total_orders = row.total_orders or 0
        total_revenue = Decimal(str(row.total_revenue or 0.00))
        completed_orders = row.completed_orders or 0
        cancelled_orders = row.cancelled_orders or 0
        avg_order_value = (
            Decimal(str(round(float(total_revenue) / completed_orders, 2)))
            if completed_orders > 0
            else Decimal("0.00")
        )
        return {
            "restaurant_id": restaurant_id,
            "total_orders": total_orders,
            "completed_orders": completed_orders,
            "cancelled_orders": cancelled_orders,
            "total_revenue": total_revenue,
            "avg_order_value": avg_order_value,
        }

    def get_agent_order_stats(self, db: Session) -> List[Dict[str, Any]]:
        delivered_count = case((Order.status == OrderStatus.DELIVERED, 1), else_=0)
        stmt = (
            select(
                Order.agent_id,
                func.count(Order.id).label("total_assigned"),
                func.coalesce(func.sum(delivered_count), 0).label("total_delivered"),
            )
            .where(Order.agent_id.is_not(None))
            .group_by(Order.agent_id)
        )
        rows = db.execute(stmt).all()
        return [
            {
                "agent_id": row.agent_id,
                "total_assigned": row.total_assigned or 0,
                "total_delivered": row.total_delivered or 0,
            }
            for row in rows
        ]

    def get_cancellation_stats(self, db: Session) -> Dict[str, Any]:
        total_orders = db.execute(select(func.count(Order.id))).scalar() or 0
        cancelled_orders = (
            db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.CANCELLED)).scalar() or 0
        )
        rejected_orders = (
            db.execute(select(func.count(Order.id)).where(Order.status == OrderStatus.REJECTED)).scalar() or 0
        )
        rate = (
            Decimal(str(round(((cancelled_orders + rejected_orders) / total_orders) * 100, 2)))
            if total_orders > 0
            else Decimal("0.00")
        )
        return {
            "total_orders": total_orders,
            "cancelled_orders": cancelled_orders,
            "rejected_orders": rejected_orders,
            "cancellation_rate_percentage": rate,
        }


order_repository = OrderRepository()
