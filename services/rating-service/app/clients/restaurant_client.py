from decimal import Decimal
from typing import Dict
import httpx
from app.core.config import settings
from app.exceptions import ServiceUnavailableException


class RestaurantServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def update_avg_rating(self, restaurant_id: int, avg_rating: Decimal) -> None:
        url = f"{settings.RESTAURANT_SERVICE_URL}/internal/restaurants/{restaurant_id}/rating"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.patch(url, json={"avg_rating": str(avg_rating)}, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"restaurant-service unreachable: {exc}",
                code="RESTAURANT_SERVICE_UNAVAILABLE",
            )

        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"restaurant-service returned {resp.status_code}",
                code="RESTAURANT_SERVICE_ERROR",
            )


restaurant_client = RestaurantServiceClient()
