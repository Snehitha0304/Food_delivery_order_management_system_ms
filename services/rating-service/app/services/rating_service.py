import logging
from typing import List
from sqlalchemy.orm import Session

from app.clients import order_client, restaurant_client
from app.core.constants import OrderStatus
from app.exceptions import NotFoundException, BadRequestException, ConflictException
from app.models.rating import Rating
from app.repositories.rating_repository import rating_repository
from app.schemas.rating import RatingCreate, RatingResponse, AgentAverageRatingResponse
from app.security import check_rating_ownership

logger = logging.getLogger("rating-service.audit")


class RatingService:
    def rate_order(self, db: Session, customer_id: int, order_id: int, data: RatingCreate) -> RatingResponse:
        order = order_client.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")

        check_rating_ownership(order["customer_id"], customer_id)

        if order["status"] != OrderStatus.DELIVERED.value:
            raise BadRequestException(
                f"Cannot rate an order that is not DELIVERED. Current status: '{order['status']}'",
                code="ORDER_NOT_DELIVERED",
            )

        existing = rating_repository.get_by_order_id(db, order_id)
        if existing:
            raise ConflictException(
                "Rating has already been submitted for this order",
                code="RATING_ALREADY_EXISTS",
            )

        rating = Rating(
            order_id=order["id"],
            customer_id=customer_id,
            restaurant_id=order["restaurant_id"],
            agent_id=order.get("agent_id"),
            restaurant_rating=data.restaurant_rating,
            agent_rating=data.agent_rating,
            comment=data.comment,
        )
        created_rating = rating_repository.create(db, rating)

        new_avg = rating_repository.get_restaurant_average_rating(db, order["restaurant_id"])
        restaurant_client.update_avg_rating(order["restaurant_id"], new_avg)

        logger.info(
            f"AUDIT: Rating submitted for order {order_id} by customer {customer_id}. "
            f"Restaurant {order['restaurant_id']} new avg={new_avg}"
        )
        return RatingResponse.model_validate(created_rating)

    def get_all_agent_averages(self, db: Session) -> List[AgentAverageRatingResponse]:
        rows = rating_repository.get_all_agent_averages(db)
        return [AgentAverageRatingResponse(**row) for row in rows]


rating_service = RatingService()
