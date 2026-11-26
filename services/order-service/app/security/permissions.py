from app.core.constants import UserRole
from app.exceptions import ForbiddenException
from app.security.jwt import AuthenticatedUser


def check_order_access(order, current_user: AuthenticatedUser) -> None:
    if current_user.role == UserRole.ADMIN:
        return
    if current_user.role == UserRole.CUSTOMER and order.customer_id == current_user.id:
        return
    if current_user.role == UserRole.RESTAURANT_OWNER and order.restaurant_owner_id == current_user.id:
        return
    if current_user.role == UserRole.DELIVERY_AGENT and order.agent_id == current_user.id:
        return
    raise ForbiddenException(
        detail="You do not have access to view this order",
        code="ORDER_ACCESS_FORBIDDEN",
    )
