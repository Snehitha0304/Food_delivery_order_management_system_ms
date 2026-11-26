from typing import Dict, List
from app.core.constants import OrderStatus
from app.exceptions import ConflictException

DELIVERY_TRANSITIONS: Dict[OrderStatus, List[OrderStatus]] = {
    OrderStatus.READY_FOR_PICKUP: [OrderStatus.PICKED_UP],
    OrderStatus.PICKED_UP: [OrderStatus.DELIVERED],
}


def validate_delivery_transition(current_status: OrderStatus, target_status: OrderStatus) -> None:
    valid_targets = DELIVERY_TRANSITIONS.get(current_status, [])
    if target_status not in valid_targets:
        raise ConflictException(
            detail=f"Invalid state transition from '{current_status.value}' to '{target_status.value}'.",
            code="INVALID_STATUS_TRANSITION",
        )
