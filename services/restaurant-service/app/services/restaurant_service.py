import logging
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.core.pagination import PageParams, PaginatedResponse
from app.exceptions import ConflictException, NotFoundException
from app.models.restaurant import Restaurant
from app.repositories.restaurant_repository import restaurant_repository
from app.schemas.restaurant import (
    RestaurantCreate,
    RestaurantUpdate,
    RestaurantOpenStatusUpdate,
    RestaurantResponse,
)

logger = logging.getLogger("restaurant-service.audit")


class RestaurantService:
    def create_restaurant(self, db: Session, owner_id: int, data: RestaurantCreate) -> RestaurantResponse:
        existing = restaurant_repository.get_by_owner_id(db, owner_id)
        if existing:
            raise ConflictException(
                "Restaurant owner already has a registered restaurant",
                code="RESTAURANT_EXISTS",
            )

        restaurant = Restaurant(
            owner_id=owner_id,
            name=data.name,
            cuisine=data.cuisine,
            city=data.city,
            address=data.address,
            opens_at=data.opens_at,
            closes_at=data.closes_at,
            is_open=data.is_open,
            avg_rating=Decimal("0.00"),
        )
        created = restaurant_repository.create(db, restaurant)
        logger.info(f"AUDIT: Restaurant ID={created.id} created by owner {owner_id}")
        return RestaurantResponse.model_validate(created)

    def get_my_restaurant(self, db: Session, owner_id: int) -> RestaurantResponse:
        restaurant = restaurant_repository.get_by_owner_id(db, owner_id)
        if not restaurant:
            raise NotFoundException("You do not have a registered restaurant", code="RESTAURANT_NOT_FOUND")
        return RestaurantResponse.model_validate(restaurant)

    def get_restaurant_by_id(self, db: Session, restaurant_id: int) -> RestaurantResponse:
        restaurant = restaurant_repository.get_by_id(db, restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant not found", code="RESTAURANT_NOT_FOUND")
        return RestaurantResponse.model_validate(restaurant)

    def update_my_restaurant(self, db: Session, owner_id: int, data: RestaurantUpdate) -> RestaurantResponse:
        restaurant = restaurant_repository.get_by_owner_id(db, owner_id)
        if not restaurant:
            raise NotFoundException("You do not have a registered restaurant", code="RESTAURANT_NOT_FOUND")

        update_dict = data.model_dump(exclude_unset=True)
        updated = restaurant_repository.update(db, restaurant, update_dict)
        logger.info(f"AUDIT: Restaurant {restaurant.id} updated by owner {owner_id}")
        return RestaurantResponse.model_validate(updated)

    def set_open_status(self, db: Session, owner_id: int, data: RestaurantOpenStatusUpdate) -> RestaurantResponse:
        restaurant = restaurant_repository.get_by_owner_id(db, owner_id)
        if not restaurant:
            raise NotFoundException("You do not have a registered restaurant", code="RESTAURANT_NOT_FOUND")

        updated = restaurant_repository.update(db, restaurant, {"is_open": data.is_open})
        logger.info(f"AUDIT: Restaurant {restaurant.id} is_open={data.is_open}")
        return RestaurantResponse.model_validate(updated)

    def update_avg_rating(self, db: Session, restaurant_id: int, avg_rating: Decimal) -> RestaurantResponse:
        updated = restaurant_repository.update_avg_rating(db, restaurant_id, avg_rating)
        if not updated:
            raise NotFoundException("Restaurant not found", code="RESTAURANT_NOT_FOUND")
        logger.info(f"AUDIT: Restaurant {restaurant_id} avg_rating updated to {avg_rating}")
        return RestaurantResponse.model_validate(updated)

    def search_restaurants(
        self,
        db: Session,
        city: Optional[str] = None,
        cuisine: Optional[str] = None,
        name: Optional[str] = None,
        params: Optional[PageParams] = None,
    ) -> PaginatedResponse[RestaurantResponse]:
        if params is None:
            params = PageParams()

        items, total = restaurant_repository.search(
            db=db,
            city=city,
            cuisine=cuisine,
            name=name,
            skip=params.offset,
            limit=params.size,
        )
        response_items = [RestaurantResponse.model_validate(item) for item in items]
        return PaginatedResponse.create(response_items, total, params)


restaurant_service = RestaurantService()
