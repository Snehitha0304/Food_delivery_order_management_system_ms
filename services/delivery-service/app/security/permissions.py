from app.exceptions import ForbiddenException


def check_assigned_agent(order_agent_id, agent_id: int) -> None:
    if order_agent_id != agent_id:
        raise ForbiddenException(
            "You are not the delivery agent assigned to this order",
            code="NOT_ASSIGNED_AGENT",
        )
