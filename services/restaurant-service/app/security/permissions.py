from app.exceptions import ForbiddenException, NotFoundException


def check_restaurant_ownership(restaurant, user_id: int) -> None:
    if not restaurant:
        raise NotFoundException("Restaurant not found", code="RESTAURANT_NOT_FOUND")
    if restaurant.owner_id != user_id:
        raise ForbiddenException(
            detail="You do not have permission to manage this restaurant",
            code="NOT_RESTAURANT_OWNER",
        )
