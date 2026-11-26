from typing import Optional, Dict, Any
import httpx

from app.core.config import settings
from app.exceptions import ServiceUnavailableException


class UserServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        url = f"{settings.USER_SERVICE_URL}/internal/users/{user_id}"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"user-service unreachable: {exc}", code="USER_SERVICE_UNAVAILABLE")

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"user-service returned {resp.status_code}",
                code="USER_SERVICE_ERROR",
            )
        return resp.json()

    def get_address(self, address_id: int) -> Optional[Dict[str, Any]]:
        url = f"{settings.USER_SERVICE_URL}/internal/addresses/{address_id}"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"user-service unreachable: {exc}", code="USER_SERVICE_UNAVAILABLE")

        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise ServiceUnavailableException(
                f"user-service returned {resp.status_code}",
                code="USER_SERVICE_ERROR",
            )
        return resp.json()


user_client = UserServiceClient()
