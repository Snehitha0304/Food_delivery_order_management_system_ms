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
            if sec_name not in merged["components"]["securitySchemes"]:
                merged["components"]["securitySchemes"][sec_name] = sec_def

    return merged
