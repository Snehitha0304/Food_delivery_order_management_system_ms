from typing import Dict, Any, Optional
import httpx
from app.core.config import settings
from app.exceptions import AppException, ServiceUnavailableException


class UserServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def create_user_profile(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{settings.USER_SERVICE_URL}/internal/users"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.post(url, json=payload, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"user-service unreachable: {exc}", code="USER_SERVICE_UNAVAILABLE")

        if resp.status_code >= 400:
            try:
                body = resp.json()
                raise AppException(
                    status_code=resp.status_code,
                    detail=body.get("detail", "Failed to create user profile"),
                    code=body.get("code", "USER_SERVICE_ERROR"),
                )
            except ValueError:
                raise ServiceUnavailableException(
                    f"user-service returned {resp.status_code}",
                    code="USER_SERVICE_ERROR",
                )
        return resp.json()

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
            raise ServiceUnavailableException(f"user-service returned {resp.status_code}", code="USER_SERVICE_ERROR")
        return resp.json()


user_client = UserServiceClient()
