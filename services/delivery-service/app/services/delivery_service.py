import logging
from typing import Optional
from sqlalchemy.orm import Session

from app.clients import user_client, order_client
from app.core.constants import OrderStatus, UserRole
from app.core.state_machine import validate_delivery_transition
from app.exceptions import NotFoundException, BadRequestException, ConflictException
from app.repositories.delivery_repository import delivery_repository
from app.schemas.delivery import OrderResponse, PaginatedOrderResponse
from app.security import check_assigned_agent

logger = logging.getLogger("delivery-service.audit")


class DeliveryService:
    def admin_assign_agent(
        self,
        db: Session,
        admin_id: int,
        order_id: int,
        agent_id: int,
    ) -> OrderResponse:
        order = order_client.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")

        if order["status"] != OrderStatus.READY_FOR_PICKUP.value:
            raise ConflictException(
                f"Agent can only be assigned when order is in '{OrderStatus.READY_FOR_PICKUP.value}' state. Current state: '{order['status']}'",
                code="INVALID_ORDER_STATE_FOR_ASSIGNMENT",
            )

        agent = user_client.get_user(agent_id)
        if not agent or agent.get("role") != UserRole.DELIVERY_AGENT.value:
            raise BadRequestException("Target user is not a valid delivery agent", code="INVALID_DELIVERY_AGENT")
        if not agent.get("is_active", False):
            raise BadRequestException("Delivery agent account is inactive", code="INACTIVE_DELIVERY_AGENT")

        updated_order = order_client.assign_agent(order_id=order_id, agent_id=agent_id, assigned_by=admin_id)
        delivery_repository.upsert_assignment(
            db=db,
            order_id=order_id,
            agent_id=agent_id,
            assigned_by=admin_id,
            status=updated_order["status"],
        )
        logger.info(f"AUDIT: Admin {admin_id} assigned agent {agent_id} to order {order_id}")
        return OrderResponse(**updated_order)

    def get_agent_orders(
        self,
        agent_id: int,
        status: Optional[OrderStatus] = None,
        page: int = 1,
        size: int = 10,
    ) -> PaginatedOrderResponse:
        data = order_client.get_agent_orders(agent_id=agent_id, status=status, page=page, size=size)
        return PaginatedOrderResponse(**data)

    def agent_update_delivery_status(
        self,
        db: Session,
        agent_id: int,
        order_id: int,
        to_status: OrderStatus,
        remark: Optional[str] = None,
    ) -> OrderResponse:
        order = order_client.get_order(order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")

        check_assigned_agent(order.get("agent_id"), agent_id)
        validate_delivery_transition(OrderStatus(order["status"]), to_status)

        updated_order = order_client.transition_order(
            order_id=order_id,
            to_status=to_status,
            actor_id=agent_id,
            actor_role=UserRole.DELIVERY_AGENT,
            remark=remark or f"Delivery status changed to {to_status.value} by delivery agent",
        )
        delivery_repository.record_status_update(
            db=db,
            order_id=order_id,
            agent_id=agent_id,
            to_status=to_status,
            remark=remark,
        )
        logger.info(f"AUDIT: Order {order_id} delivery status -> {to_status.value} by agent {agent_id}")
        return OrderResponse(**updated_order)


delivery_service = DeliveryService()
