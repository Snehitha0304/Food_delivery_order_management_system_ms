import re
from typing import Dict, Any, Tuple
import httpx
from fastapi import Request, Response

from app.core.config import settings
from app.exceptions import ForbiddenException, NotFoundException, ServiceUnavailableException

HOP_BY_HOP_HEADERS = {
    "host",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
    "x-internal-api-key",
}

MENU_ROUTE_PATTERNS = [
    re.compile(r"^/api/v1/menu-items(?:/.*)?$"),
    re.compile(r"^/api/v1/restaurants/me/menu-categories(?:/.*)?$"),
    re.compile(r"^/api/v1/restaurants/me/menu-items(?:/.*)?$"),
    re.compile(r"^/api/v1/restaurants/\d+/menu/?$"),
]

DELIVERY_ORDER_PATTERNS = [
    re.compile(r"^/api/v1/orders/agent/?$"),
    re.compile(r"^/api/v1/orders/\d+/assign-agent/?$"),
    re.compile(r"^/api/v1/orders/\d+/delivery-status/?$"),
]

RATING_ORDER_PATTERN = re.compile(r"^/api/v1/orders/\d+/rating/?$")


def resolve_target_service(path: str) -> Tuple[str, str]:
    if path.startswith("/internal"):
        raise ForbiddenException("Direct access to internal endpoints is forbidden", code="INTERNAL_ROUTE_FORBIDDEN")

    if path.startswith("/api/v1/auth"):
        return "auth-service", settings.AUTH_SERVICE_URL

    if path.startswith("/api/v1/customer") or path.startswith("/api/v1/addresses"):
        return "user-service", settings.USER_SERVICE_URL

    if any(pattern.match(path) for pattern in MENU_ROUTE_PATTERNS):
        return "menu-service", settings.MENU_SERVICE_URL

    if path.startswith("/api/v1/restaurants"):
        return "restaurant-service", settings.RESTAURANT_SERVICE_URL

    if any(pattern.match(path) for pattern in DELIVERY_ORDER_PATTERNS):
        return "delivery-service", settings.DELIVERY_SERVICE_URL

    if RATING_ORDER_PATTERN.match(path):
        return "rating-service", settings.RATING_SERVICE_URL

    if path.startswith("/api/v1/orders"):
        return "order-service", settings.ORDER_SERVICE_URL

    if path.startswith("/api/v1/reports"):
        return "report-service", settings.REPORT_SERVICE_URL

    raise NotFoundException(f"No microservice route matched '{path}'", code="ROUTE_NOT_FOUND")


async def forward_request(request: Request) -> Response:
    path = request.url.path
    service_name, base_url = resolve_target_service(path)
    target_url = f"{base_url}{path}"
    if request.url.query:
        target_url = f"{target_url}?{request.url.query}"

    headers = {
        k: v for k, v in request.headers.items() if k.lower() not in HOP_BY_HOP_HEADERS
    }
    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            upstream_resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
    except httpx.RequestError as exc:
        raise ServiceUnavailableException(
            detail=f"Downstream service '{service_name}' is unreachable: {exc}",
            code="DOWNSTREAM_UNAVAILABLE",
        )

    excluded_resp_headers = {"content-encoding", "transfer-encoding", "connection", "content-length"}
    resp_headers = {
        k: v for k, v in upstream_resp.headers.items() if k.lower() not in excluded_resp_headers
    }
    resp_headers["X-Served-By"] = service_name

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )


async def check_all_services_health() -> Dict[str, Any]:
    services = {
        "auth-service": settings.AUTH_SERVICE_URL,
        "user-service": settings.USER_SERVICE_URL,
        "restaurant-service": settings.RESTAURANT_SERVICE_URL,
        "menu-service": settings.MENU_SERVICE_URL,
        "order-service": settings.ORDER_SERVICE_URL,
        "delivery-service": settings.DELIVERY_SERVICE_URL,
        "rating-service": settings.RATING_SERVICE_URL,
        "report-service": settings.REPORT_SERVICE_URL,
    }
    results: Dict[str, Any] = {}
    all_healthy = True

    async with httpx.AsyncClient(timeout=5.0) as client:
        for name, base_url in services.items():
            try:
                resp = await client.get(f"{base_url}/health")
                data = resp.json()
                results[name] = data
                if resp.status_code != 200 or data.get("status") != "healthy":
                    all_healthy = False
            except Exception as exc:
                all_healthy = False
                results[name] = {"service": name, "status": "unreachable", "error": str(exc)}

    return {
        "gateway": "healthy" if all_healthy else "degraded",
        "services": results,
    }
