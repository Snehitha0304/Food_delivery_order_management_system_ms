from sqlalchemy import Column, Integer, Text, CheckConstraint
from app.core.database import Base
from app.models.base import TimestampMixin


class Rating(Base, TimestampMixin):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    # Cross-service IDs stored locally in rating_db (no cross-DB FKs)
    order_id = Column(Integer, unique=True, nullable=False, index=True)
    customer_id = Column(Integer, nullable=False, index=True)
    restaurant_id = Column(Integer, nullable=False, index=True)
    agent_id = Column(Integer, nullable=True, index=True)
    restaurant_rating = Column(Integer, nullable=False)
    agent_rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("restaurant_rating >= 1 AND restaurant_rating <= 5", name="check_restaurant_rating_range"),
        CheckConstraint("agent_rating >= 1 AND agent_rating <= 5", name="check_agent_rating_range"),
    )
