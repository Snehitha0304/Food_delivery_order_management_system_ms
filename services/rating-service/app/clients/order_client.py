from typing import Optional, Dict, Any
import httpx
from app.core.config import settings
from app.exceptions import ServiceUnavailableException


class OrderServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        url = f"{settings.ORDER_SERVICE_URL}/internal/orders/{order_id}"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"order-service unreachable: {exc}", code="ORDER_SERVICE_UNAVAILABLE")

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ServiceUnavailableException(f"order-service returned {resp.status_code}", code="ORDER_SERVICE_ERROR")
        return resp.json()


order_client = OrderServiceClient()
