from typing import Optional, List, Dict, Any
import httpx
from app.core.config import settings
from app.exceptions import ServiceUnavailableException


class BaseInternalClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def _get(self, url: str, service_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, params=params, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"{service_name} unreachable: {exc}",
                code=f"{service_name.upper().replace('-', '_')}_UNAVAILABLE",
            )
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"{service_name} returned {resp.status_code}",
                code=f"{service_name.upper().replace('-', '_')}_ERROR",
            )
        return resp.json()


class UserServiceClient(BaseInternalClient):
    def list_delivery_agents(self) -> List[Dict[str, Any]]:
        return self._get(f"{settings.USER_SERVICE_URL}/internal/users/agents", "user-service") or []


class RestaurantServiceClient(BaseInternalClient):
    def get_restaurant_by_owner(self, owner_id: int) -> Optional[Dict[str, Any]]:
        return self._get(
            f"{settings.RESTAURANT_SERVICE_URL}/internal/restaurants/by-owner/{owner_id}",
            "restaurant-service",
        )


class OrderServiceClient(BaseInternalClient):
    def get_sales_stats(self, restaurant_id: Optional[int] = None) -> Dict[str, Any]:
        params = {"restaurant_id": restaurant_id} if restaurant_id is not None else None
        return self._get(
            f"{settings.ORDER_SERVICE_URL}/internal/orders/stats/sales",
            "order-service",
            params=params,
        )

    def get_agent_stats(self) -> List[Dict[str, Any]]:
        return self._get(f"{settings.ORDER_SERVICE_URL}/internal/orders/stats/agents", "order-service") or []

    def get_cancellation_stats(self) -> Dict[str, Any]:
        return self._get(
            f"{settings.ORDER_SERVICE_URL}/internal/orders/stats/cancellation-rate",
            "order-service",
        )


class RatingServiceClient(BaseInternalClient):
    def get_agent_averages(self) -> List[Dict[str, Any]]:
        return self._get(
            f"{settings.RATING_SERVICE_URL}/internal/ratings/agents/averages",
            "rating-service",
        ) or []


user_client = UserServiceClient()
restaurant_client = RestaurantServiceClient()
order_client = OrderServiceClient()
rating_client = RatingServiceClient()
