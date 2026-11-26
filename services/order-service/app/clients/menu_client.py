from typing import List, Dict, Any
import httpx

from app.core.config import settings
from app.exceptions import ServiceUnavailableException


class MenuServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def get_menu_items_batch(self, item_ids: List[int]) -> List[Dict[str, Any]]:
        url = f"{settings.MENU_SERVICE_URL}/internal/menu-items/batch"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.post(url, json={"item_ids": item_ids}, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(
                f"menu-service unreachable: {exc}",
                code="MENU_SERVICE_UNAVAILABLE",
            )

        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"menu-service returned {resp.status_code}",
                code="MENU_SERVICE_ERROR",
            )
        return resp.json()


menu_client = MenuServiceClient()
