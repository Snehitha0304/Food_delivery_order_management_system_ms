from app.exceptions import ForbiddenException


def check_rating_ownership(order_customer_id: int, customer_id: int) -> None:
    if order_customer_id != customer_id:
        raise ForbiddenException(
            "Only the customer who placed the order can rate it",
            code="RATING_FORBIDDEN",
        )
