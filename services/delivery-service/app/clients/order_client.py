from typing import Optional, Dict, Any
import httpx
from app.core.config import settings
from app.core.constants import OrderStatus, UserRole
from app.exceptions import AppException, ServiceUnavailableException


class OrderServiceClient:
    def _headers(self) -> Dict[str, str]:
        return {"X-Internal-API-Key": settings.INTERNAL_API_KEY}

    def _handle_error(self, resp: httpx.Response) -> None:
        try:
            body = resp.json()
            detail = body.get("detail", "Order service error")
            code = body.get("code", f"ORDER_SERVICE_{resp.status_code}")
        except Exception:
            detail = resp.text or "Order service error"
            code = f"ORDER_SERVICE_{resp.status_code}"
        raise AppException(status_code=resp.status_code, detail=detail, code=code)

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
            self._handle_error(resp)
        return resp.json()

    def assign_agent(self, order_id: int, agent_id: int, assigned_by: int) -> Dict[str, Any]:
        url = f"{settings.ORDER_SERVICE_URL}/internal/orders/{order_id}/assign-agent"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.patch(
                    url,
                    json={"agent_id": agent_id, "assigned_by": assigned_by},
                    headers=self._headers(),
                )
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"order-service unreachable: {exc}", code="ORDER_SERVICE_UNAVAILABLE")

        if resp.status_code >= 400:
            self._handle_error(resp)
        return resp.json()

    def transition_order(
        self,
        order_id: int,
        to_status: OrderStatus,
        actor_id: int,
        actor_role: UserRole,
        remark: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{settings.ORDER_SERVICE_URL}/internal/orders/{order_id}/transition"
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.patch(
                    url,
                    json={
                        "to_status": to_status.value,
                        "actor_id": actor_id,
                        "actor_role": actor_role.value,
                        "remark": remark,
                    },
                    headers=self._headers(),
                )
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"order-service unreachable: {exc}", code="ORDER_SERVICE_UNAVAILABLE")

        if resp.status_code >= 400:
            self._handle_error(resp)
        return resp.json()

    def get_agent_orders(
        self,
        agent_id: int,
        status: Optional[OrderStatus] = None,
        page: int = 1,
        size: int = 10,
    ) -> Dict[str, Any]:
        url = f"{settings.ORDER_SERVICE_URL}/internal/orders/by-agent/{agent_id}"
        params: Dict[str, Any] = {"page": page, "size": size}
        if status is not None:
            params["status"] = status.value
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = client.get(url, params=params, headers=self._headers())
        except httpx.RequestError as exc:
            raise ServiceUnavailableException(f"order-service unreachable: {exc}", code="ORDER_SERVICE_UNAVAILABLE")

        if resp.status_code >= 400:
            self._handle_error(resp)
        return resp.json()


order_client = OrderServiceClient()
