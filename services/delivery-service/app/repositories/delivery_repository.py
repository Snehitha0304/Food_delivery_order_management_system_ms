from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import OrderStatus
from app.models.delivery import Delivery, DeliveryEvent


class DeliveryRepository:
    def get_by_order_id(self, db: Session, order_id: int) -> Optional[Delivery]:
        stmt = select(Delivery).where(Delivery.order_id == order_id)
        return db.execute(stmt).scalars().first()

    def upsert_assignment(self, db: Session, order_id: int, agent_id: int, assigned_by: int, status: str) -> Delivery:
        now_utc = datetime.now(timezone.utc)
        delivery = self.get_by_order_id(db, order_id)
        if delivery:
            delivery.agent_id = agent_id
            delivery.assigned_by = assigned_by
            delivery.status = status
            delivery.assigned_at = now_utc
        else:
            delivery = Delivery(
                order_id=order_id,
                agent_id=agent_id,
                assigned_by=assigned_by,
                status=status,
                assigned_at=now_utc,
            )
            db.add(delivery)
            db.flush()

        db.add(
            DeliveryEvent(
                delivery_id=delivery.id,
                status=status,
                actor_id=assigned_by,
                remark=f"Delivery agent {agent_id} assigned",
                occurred_at=now_utc,
            )
        )
        db.commit()
        db.refresh(delivery)
        return delivery

    def record_status_update(
        self,
        db: Session,
        order_id: int,
        agent_id: int,
        to_status: OrderStatus,
        remark: Optional[str] = None,
    ) -> Delivery:
        now_utc = datetime.now(timezone.utc)
        delivery = self.get_by_order_id(db, order_id)
        if not delivery:
            delivery = Delivery(
                order_id=order_id,
                agent_id=agent_id,
                assigned_by=agent_id,
                status=to_status.value,
                assigned_at=now_utc,
            )
            db.add(delivery)
            db.flush()

        delivery.status = to_status.value
        if to_status == OrderStatus.PICKED_UP:
            delivery.picked_up_at = now_utc
        elif to_status == OrderStatus.DELIVERED:
            delivery.delivered_at = now_utc

        db.add(
            DeliveryEvent(
                delivery_id=delivery.id,
                status=to_status.value,
                actor_id=agent_id,
                remark=remark or f"Status updated to {to_status.value}",
                occurred_at=now_utc,
            )
        )
        db.commit()
        db.refresh(delivery)
        return delivery


delivery_repository = DeliveryRepository()
