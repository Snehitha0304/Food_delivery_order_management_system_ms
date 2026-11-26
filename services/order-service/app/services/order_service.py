import logging
from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from app.clients import user_client, restaurant_client, menu_client
from app.core.constants import OrderStatus, UserRole
from app.core.pagination import PageParams, PaginatedResponse
from app.core.state_machine import validate_transition
from app.exceptions import NotFoundException, BadRequestException, ForbiddenException
from app.models.order import Order
from app.models.order_item import OrderItem
from app.repositories.order_repository import order_repository
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderDetailResponse,
    OrderItemResponse,
    OrderStatusHistoryResponse,
    InternalOrderSummary,
    SalesStatsResponse,
    AgentOrderStatsResponse,
    CancellationStatsResponse,
)
from app.security import AuthenticatedUser, check_order_access
from app.utils import calculate_order_totals, round_currency, generate_order_number

logger = logging.getLogger("order-service.audit")


class OrderService:
    def create_order(self, db: Session, customer_id: int, data: OrderCreate) -> OrderResponse:
        # 1. Verify restaurant exists & is open via restaurant-service
        restaurant = restaurant_client.get_restaurant(data.restaurant_id)
        if not restaurant:
            raise NotFoundException("Restaurant not found", code="RESTAURANT_NOT_FOUND")
        if not restaurant.get("is_open", False):
            raise BadRequestException(
                "Cannot place order: Restaurant is currently closed",
                code="RESTAURANT_CLOSED",
            )

        # 2. Verify address exists & belongs to customer via user-service
        address = user_client.get_address(data.address_id)
        if not address or address.get("user_id") != customer_id:
            raise BadRequestException("Invalid delivery address", code="INVALID_ADDRESS")

        # 3. Fetch menu items from menu-service & validate
        item_ids = [item_in.menu_item_id for item_in in data.items]
        catalog_items = menu_client.get_menu_items_batch(item_ids)
        items_map = {item["id"]: item for item in catalog_items}

        if len(items_map) != len(set(item_ids)):
            raise BadRequestException("One or more menu items do not exist", code="INVALID_MENU_ITEM")

        order_items: List[OrderItem] = []
        pricing_inputs = []

        for item_in in data.items:
            catalog_item = items_map[item_in.menu_item_id]

            if catalog_item["restaurant_id"] != data.restaurant_id:
                raise BadRequestException(
                    "All items in an order must be from the same restaurant",
                    code="MULTIPLE_RESTAURANTS_NOT_ALLOWED",
                )

            if catalog_item.get("is_deleted") or not catalog_item.get("is_available"):
                raise BadRequestException(
                    f"Item '{catalog_item['name']}' is currently unavailable or has been removed",
                    code="ITEM_UNAVAILABLE",
                )

            # Server-side pricing integrity: ignore any client-supplied price
            unit_price = round_currency(Decimal(str(catalog_item["price"])))
            line_total = round_currency(unit_price * Decimal(item_in.quantity))
            pricing_inputs.append((unit_price, item_in.quantity))

            order_items.append(
                OrderItem(
                    menu_item_id=catalog_item["id"],
                    item_name_snapshot=catalog_item["name"],
                    unit_price_snapshot=unit_price,
                    quantity=item_in.quantity,
                    line_total=line_total,
                )
            )

        item_total, tax_amount, delivery_fee, grand_total = calculate_order_totals(pricing_inputs)

        order = Order(
            order_no=generate_order_number(),
            customer_id=customer_id,
            restaurant_id=data.restaurant_id,
            restaurant_owner_id=restaurant["owner_id"],
            address_id=data.address_id,
            status=OrderStatus.PLACED,
            item_total=item_total,
            tax_amount=tax_amount,
            delivery_fee=delivery_fee,
            grand_total=grand_total,
        )

        created_order = order_repository.create(db, order, order_items, customer_id)
        logger.info(f"AUDIT: Order '{created_order.order_no}' created by customer {customer_id} total={grand_total}")
        return OrderResponse.model_validate(created_order)

    def cancel_order(self, db: Session, customer_id: int, order_id: int) -> OrderResponse:
        order = order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")
        if order.customer_id != customer_id:
            raise ForbiddenException("You can only cancel your own orders", code="ORDER_OWNERSHIP_VIOLATION")

        validate_transition(order.status, OrderStatus.CANCELLED, UserRole.CUSTOMER)
        updated_order = order_repository.record_transition(
            db=db,
            order=order,
            to_status=OrderStatus.CANCELLED,
            user_id=customer_id,
            remark="Order cancelled by customer",
        )
        logger.info(f"AUDIT: Order {order.id} cancelled by customer {customer_id}")
        return OrderResponse.model_validate(updated_order)

    def get_customer_orders(
        self,
        db: Session,
        customer_id: int,
        params: Optional[PageParams] = None,
    ) -> PaginatedResponse[OrderResponse]:
        if params is None:
            params = PageParams()
        orders, total = order_repository.get_by_customer_id(db, customer_id, skip=params.offset, limit=params.size)
        return PaginatedResponse.create([OrderResponse.model_validate(o) for o in orders], total, params)

    def get_order_detail(
        self,
        db: Session,
        current_user: AuthenticatedUser,
        order_id: int,
    ) -> OrderDetailResponse:
        order = order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")

        check_order_access(order, current_user)

        order_dict = OrderResponse.model_validate(order).model_dump()
        order_dict["items"] = [OrderItemResponse.model_validate(i) for i in order.items]
        order_dict["status_history"] = [OrderStatusHistoryResponse.model_validate(h) for h in order.status_history]

        customer_profile = user_client.get_user(order.customer_id)
        order_dict["customer_name"] = customer_profile["full_name"] if customer_profile else None

        is_agent = current_user.role == UserRole.DELIVERY_AGENT
        if is_agent and order.status not in [OrderStatus.PICKED_UP, OrderStatus.DELIVERED]:
            order_dict["customer_phone"] = None
        else:
            order_dict["customer_phone"] = customer_profile["phone"] if customer_profile else None

        return OrderDetailResponse(**order_dict)

    def restaurant_get_orders(
        self,
        db: Session,
        owner_id: int,
        status: Optional[OrderStatus] = None,
        params: Optional[PageParams] = None,
    ) -> PaginatedResponse[OrderResponse]:
        restaurant = restaurant_client.get_restaurant_by_owner(owner_id)
        if not restaurant:
            raise ForbiddenException("You do not have a registered restaurant", code="RESTAURANT_NOT_FOUND")

        if params is None:
            params = PageParams()

        orders, total = order_repository.get_by_restaurant_id(
            db=db,
            restaurant_id=restaurant["id"],
            status=status,
            skip=params.offset,
            limit=params.size,
        )
        return PaginatedResponse.create([OrderResponse.model_validate(o) for o in orders], total, params)

    def restaurant_update_status(
        self,
        db: Session,
        owner_id: int,
        order_id: int,
        to_status: OrderStatus,
        remark: Optional[str] = None,
    ) -> OrderResponse:
        restaurant = restaurant_client.get_restaurant_by_owner(owner_id)
        if not restaurant:
            raise ForbiddenException("You do not have a registered restaurant", code="RESTAURANT_NOT_FOUND")

        order = order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")
        if order.restaurant_id != restaurant["id"]:
            raise ForbiddenException("Order does not belong to your restaurant", code="ORDER_OWNERSHIP_VIOLATION")

        validate_transition(order.status, to_status, UserRole.RESTAURANT_OWNER)

        updated_order = order_repository.record_transition(
            db=db,
            order=order,
            to_status=to_status,
            user_id=owner_id,
            remark=remark or f"Status changed to {to_status.value} by restaurant owner",
        )
        logger.info(f"AUDIT: Order {order.id} transitioned to {to_status.value} by owner {owner_id}")
        return OrderResponse.model_validate(updated_order)

    # Internal service-to-service operations
    def get_internal_order(self, db: Session, order_id: int) -> InternalOrderSummary:
        order = order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")
        return InternalOrderSummary.model_validate(order)

    def internal_assign_agent(self, db: Session, order_id: int, agent_id: int, assigned_by: int) -> OrderResponse:
        order = order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")
        updated = order_repository.assign_agent(db, order, agent_id, assigned_by)
        return OrderResponse.model_validate(updated)

    def internal_transition(
        self,
        db: Session,
        order_id: int,
        to_status: OrderStatus,
        actor_id: int,
        actor_role: UserRole,
        remark: Optional[str] = None,
    ) -> OrderResponse:
        order = order_repository.get_by_id(db, order_id)
        if not order:
            raise NotFoundException("Order not found", code="ORDER_NOT_FOUND")
        validate_transition(order.status, to_status, actor_role)
        updated = order_repository.record_transition(
            db=db,
            order=order,
            to_status=to_status,
            user_id=actor_id,
            remark=remark or f"Status changed to {to_status.value}",
        )
        return OrderResponse.model_validate(updated)

    def internal_get_agent_orders(
        self,
        db: Session,
        agent_id: int,
        status: Optional[OrderStatus] = None,
        params: Optional[PageParams] = None,
    ) -> PaginatedResponse[OrderResponse]:
        if params is None:
            params = PageParams()
        orders, total = order_repository.get_by_agent_id(
            db=db,
            agent_id=agent_id,
            status=status,
            skip=params.offset,
            limit=params.size,
        )
        return PaginatedResponse.create([OrderResponse.model_validate(o) for o in orders], total, params)

    def get_sales_stats(self, db: Session, restaurant_id: Optional[int] = None) -> SalesStatsResponse:
        return SalesStatsResponse(**order_repository.get_sales_stats(db, restaurant_id))

    def get_agent_order_stats(self, db: Session) -> List[AgentOrderStatsResponse]:
        return [AgentOrderStatsResponse(**row) for row in order_repository.get_agent_order_stats(db)]

    def get_cancellation_stats(self, db: Session) -> CancellationStatsResponse:
        return CancellationStatsResponse(**order_repository.get_cancellation_stats(db))


order_service = OrderService()
