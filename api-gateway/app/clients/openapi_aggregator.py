import asyncio
from typing import Any, Dict, List, Tuple
import httpx

from app.core.config import settings

MICROSERVICE_SPECS: List[Tuple[str, str]] = [
    ("auth-service", settings.AUTH_SERVICE_URL),
    ("user-service", settings.USER_SERVICE_URL),
    ("restaurant-service", settings.RESTAURANT_SERVICE_URL),
    ("menu-service", settings.MENU_SERVICE_URL),
    ("order-service", settings.ORDER_SERVICE_URL),
    ("delivery-service", settings.DELIVERY_SERVICE_URL),
    ("rating-service", settings.RATING_SERVICE_URL),
    ("report-service", settings.REPORT_SERVICE_URL),
]

SERVICE_DISPLAY_NAMES: Dict[str, str] = {
    "auth-service": "Auth Service (8008)",
    "user-service": "User Service (8001)",
    "restaurant-service": "Restaurant Service (8002)",
    "menu-service": "Menu Service (8007)",
    "order-service": "Order Service (8003)",
    "delivery-service": "Delivery Service (8004)",
    "rating-service": "Rating Service (8005)",
    "report-service": "Report Service (8006)",
}

SERVICE_SWAGGER_URLS: List[Dict[str, str]] = [
    {"name": "All Microservices (Unified)", "url": "/openapi.json"},
    *[
        {"name": SERVICE_DISPLAY_NAMES[name], "url": f"/openapi/{name}.json"}
        for name, _url in MICROSERVICE_SPECS
    ],
]

ORDERED_TAGS = [
    {"name": "Gateway Health", "description": "Aggregated health status across all 8 microservices"},
    {"name": "Authentication", "description": "Registration, Login & Admin User Onboarding (auth-service)"},
    {"name": "Customer", "description": "Customer Profile & Delivery Addresses (user-service)"},
    {"name": "Restaurants", "description": "Restaurant Discovery & Management (restaurant-service)"},
    {"name": "Menu", "description": "Menu Categories & Menu Items (menu-service)"},
    {"name": "Orders", "description": "Order Placement, Tracking & State Machine (order-service)"},
    {"name": "Delivery", "description": "Delivery Agent Assignment & Dispatch Lifecycle (delivery-service)"},
    {"name": "Ratings", "description": "Post-Delivery Restaurant & Agent Ratings (rating-service)"},
    {"name": "Reports", "description": "Sales, Agent Performance & Cancellation Analytics (report-service)"},
]


async def _fetch_service_openapi(client: httpx.AsyncClient, name: str, base_url: str) -> Tuple[str, Dict[str, Any] | None]:
    try:
        resp = await client.get(f"{base_url}/openapi.json")
        if resp.status_code == 200:
            return name, resp.json()
    except Exception:
        pass
    return name, None


async def build_aggregated_openapi(gateway_schema: Dict[str, Any]) -> Dict[str, Any]:
    merged: Dict[str, Any] = {
        "openapi": gateway_schema.get("openapi", "3.1.0"),
        "info": {
            "title": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "description": (
                "Unified Swagger UI aggregating all 8 Food Delivery Microservices: "
                "Authentication, Customer, Restaurants, Menu, Orders, Delivery, Ratings, and Reports."
            ),
        },
        "tags": list(ORDERED_TAGS),
        "paths": {},
        "components": {
            "schemas": {},
            "securitySchemes": {
                "OAuth2PasswordBearer": {
                    "type": "oauth2",
                    "flows": {
                        "password": {
                            "scopes": {},
                            "tokenUrl": "/api/v1/auth/login",
                        }
                    },
                }
            },
        },
    }

    # Include gateway's own /health & /api/v1/health endpoints
    for path, methods in gateway_schema.get("paths", {}).items():
        if path in ("/health", "/api/v1/health"):
            merged["paths"][path] = methods

    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [_fetch_service_openapi(client, name, url) for name, url in MICROSERVICE_SPECS]
        results = await asyncio.gather(*tasks)

    for _svc_name, spec in results:
        if not spec:
            continue

        # Merge public /api/v1/* paths (skip /internal/* and downstream /health duplicates)
        for path, methods in spec.get("paths", {}).items():
            if not path.startswith("/api/v1/") or path == "/api/v1/health":
                continue
            if path not in merged["paths"]:
                merged["paths"][path] = {}
            for method, operation in methods.items():
                merged["paths"][path][method] = operation

        # Merge component schemas & security schemes
        components = spec.get("components", {})
        for schema_name, schema_def in components.get("schemas", {}).items():
            if schema_name not in merged["components"]["schemas"]:
                merged["components"]["schemas"][schema_name] = schema_def
        for sec_name, sec_def in components.get("securitySchemes", {}).items():
            if sec_name not in merged["components"]["schemas"] and sec_name not in merged["components"]["securitySchemes"]:
                merged["components"]["securitySchemes"][sec_name] = sec_def

    return merged


async def build_service_openapi(service_name: str) -> Dict[str, Any] | None:
    """Fetch a single microservice's public OpenAPI schema (excluding /internal/*)."""
    specs_map = dict(MICROSERVICE_SPECS)
    base_url = specs_map.get(service_name)
    if not base_url:
        return None

    async with httpx.AsyncClient(timeout=5.0) as client:
        _, spec = await _fetch_service_openapi(client, service_name, base_url)
    if not spec:
        return None

    filtered_paths: Dict[str, Any] = {
        path: methods
        for path, methods in spec.get("paths", {}).items()
        if path.startswith("/api/v1/") and path != "/api/v1/health"
    }
    components = dict(spec.get("components", {}))
    security_schemes = dict(components.get("securitySchemes", {}))
    security_schemes.setdefault(
        "OAuth2PasswordBearer",
        {
            "type": "oauth2",
            "flows": {
                "password": {
                    "scopes": {},
                    "tokenUrl": "/api/v1/auth/login",
                }
            },
        },
    )
    components["securitySchemes"] = security_schemes

    return {
        "openapi": spec.get("openapi", "3.1.0"),
        "info": spec.get(
            "info",
            {
                "title": SERVICE_DISPLAY_NAMES.get(service_name, service_name),
                "version": settings.VERSION,
            },
        ),
        "paths": filtered_paths,
        "components": components,
    }
