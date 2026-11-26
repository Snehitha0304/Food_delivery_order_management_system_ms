from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.rating import Rating


class RatingRepository:
    def create(self, db: Session, rating: Rating) -> Rating:
        db.add(rating)
        db.commit()
        db.refresh(rating)
        return rating

    def get_by_order_id(self, db: Session, order_id: int) -> Optional[Rating]:
        stmt = select(Rating).where(Rating.order_id == order_id)
        return db.execute(stmt).scalars().first()

    def get_restaurant_average_rating(self, db: Session, restaurant_id: int) -> Decimal:
        stmt = select(func.avg(Rating.restaurant_rating)).where(Rating.restaurant_id == restaurant_id)
        avg_val = db.execute(stmt).scalar()
        if avg_val is not None:
            return Decimal(str(round(float(avg_val), 2)))
        return Decimal("0.00")

    def get_all_agent_averages(self, db: Session) -> List[Dict[str, Any]]:
        stmt = (
            select(
                Rating.agent_id,
                func.avg(Rating.agent_rating).label("avg_rating"),
            )
            .where(Rating.agent_id.is_not(None))
            .group_by(Rating.agent_id)
        )
        rows = db.execute(stmt).all()
        return [
            {
                "agent_id": row.agent_id,
                "avg_rating": Decimal(str(round(float(row.avg_rating), 2))) if row.avg_rating is not None else None,
            }
            for row in rows
        ]


rating_repository = RatingRepository()
