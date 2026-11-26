from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.exceptions import ServiceUnavailableException


class RestaurantServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def get_restaurant(self, restaurant_id: int) -> Optional[Dict[str, Any]]:
        url = f"{settings.RESTAURANT_SERVICE_URL}/internal/restaurants/{restaurant_id}"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"restaurant-service unreachable: {exc}",
                code="RESTAURANT_SERVICE_UNAVAILABLE",
            )

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"restaurant-service returned {resp.status_code}",
                code="RESTAURANT_SERVICE_ERROR",
            )
        return resp.json()

    def get_restaurant_by_owner(self, owner_id: int) -> Optional[Dict[str, Any]]:
        url = f"{settings.RESTAURANT_SERVICE_URL}/internal/restaurants/by-owner/{owner_id}"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"restaurant-service unreachable: {exc}",
                code="RESTAURANT_SERVICE_UNAVAILABLE",
            )

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"restaurant-service returned {resp.status_code}",
                code="RESTAURANT_SERVICE_ERROR",
            )
        return resp.json()


restaurant_client = RestaurantServiceClient()
