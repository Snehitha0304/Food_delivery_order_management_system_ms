from decimal import Decimal
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.restaurant import Restaurant


class RestaurantRepository:
    def get_by_id(self, db: Session, restaurant_id: int) -> Optional[Restaurant]:
        return db.get(Restaurant, restaurant_id)

    def get_by_owner_id(self, db: Session, owner_id: int) -> Optional[Restaurant]:
        stmt = select(Restaurant).where(Restaurant.owner_id == owner_id)
        return db.execute(stmt).scalars().first()

    def create(self, db: Session, restaurant: Restaurant) -> Restaurant:
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)
        return restaurant

    def update(self, db: Session, restaurant: Restaurant, update_data: dict) -> Restaurant:
        for field, value in update_data.items():
            if value is not None:
                setattr(restaurant, field, value)
        db.commit()
        db.refresh(restaurant)
        return restaurant

    def search(
        self,
        db: Session,
        city: Optional[str] = None,
        cuisine: Optional[str] = None,
        name: Optional[str] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Tuple[List[Restaurant], int]:
        stmt = select(Restaurant)
        count_stmt = select(func.count(Restaurant.id))

        if city:
            stmt = stmt.where(Restaurant.city.ilike(f"%{city}%"))
            count_stmt = count_stmt.where(Restaurant.city.ilike(f"%{city}%"))
        if cuisine:
            stmt = stmt.where(Restaurant.cuisine.ilike(f"%{cuisine}%"))
            count_stmt = count_stmt.where(Restaurant.cuisine.ilike(f"%{cuisine}%"))
        if name:
            stmt = stmt.where(Restaurant.name.ilike(f"%{name}%"))
            count_stmt = count_stmt.where(Restaurant.name.ilike(f"%{name}%"))

        total = db.execute(count_stmt).scalar() or 0
        items = list(db.execute(stmt.offset(skip).limit(limit).order_by(Restaurant.name.asc())).scalars().all())
        return items, total

    def update_avg_rating(self, db: Session, restaurant_id: int, avg_rating: Decimal) -> Optional[Restaurant]:
        restaurant = self.get_by_id(db, restaurant_id)
        if restaurant:
            restaurant.avg_rating = avg_rating
            db.commit()
            db.refresh(restaurant)
        return restaurant


restaurant_repository = RestaurantRepository()
