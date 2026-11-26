from app.exceptions import ForbiddenException, NotFoundException


def check_category_ownership(category, restaurant_id: int) -> None:
    if not category:
        raise NotFoundException("Menu category not found", code="CATEGORY_NOT_FOUND")
    if category.restaurant_id != restaurant_id:
        raise ForbiddenException(
            "You do not have permission to manage this category",
            code="CATEGORY_OWNERSHIP_VIOLATION",
        )


def check_item_ownership(item, restaurant_id: int) -> None:
    if not item:
        raise NotFoundException("Menu item not found", code="ITEM_NOT_FOUND")
    if item.restaurant_id != restaurant_id:
        raise ForbiddenException(
            "You cannot modify another restaurant's menu items",
            code="ITEM_OWNERSHIP_VIOLATION",
        )
