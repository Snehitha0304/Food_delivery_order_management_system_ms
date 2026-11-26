from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimestampMixin, utc_now


class Delivery(Base, TimestampMixin):
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, unique=True, nullable=False, index=True)
    agent_id = Column(Integer, nullable=False, index=True)
    assigned_by = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, index=True)
    assigned_at = Column(DateTime, default=utc_now, nullable=False)
    picked_up_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    events = relationship("DeliveryEvent", back_populates="delivery", cascade="all, delete-orphan")


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(Integer, ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    actor_id = Column(Integer, nullable=False)
    remark = Column(Text, nullable=True)
    occurred_at = Column(DateTime, default=utc_now, nullable=False)

    delivery = relationship("Delivery", back_populates="events")
