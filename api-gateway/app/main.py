import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse

from app.clients import build_aggregated_openapi, build_service_openapi, SERVICE_SWAGGER_URLS
from app.core.config import settings
from app.exceptions import register_exception_handlers
from app.routers import health, gateway

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Single Entry-Point API Gateway routing /api/v1/* requests to "
        "auth-service, user-service, restaurant-service, menu-service, order-service, "
        "delivery-service, rating-service, and report-service."
    ),
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health.router)


@app.get("/openapi.json", include_in_schema=False)
async def aggregated_openapi():
    base_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    return await build_aggregated_openapi(base_schema)


@app.get("/openapi/{service_name}.json", include_in_schema=False)
async def service_openapi(service_name: str):
    schema = await build_service_openapi(service_name)
    if schema is None:
        raise HTTPException(
            status_code=404,
            detail=f"OpenAPI schema unavailable for service '{service_name}'",
        )
    return schema


@app.get("/docs", include_in_schema=False)
async def swagger_ui():
    urls_json = json.dumps(SERVICE_SWAGGER_URLS)
    title = f"{settings.PROJECT_NAME} - Swagger UI"
    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css" />
  <style>
    body {{ margin: 0; padding: 0; }}
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
  <script>
    window.onload = function () {{
      SwaggerUIBundle({{
        urls: {urls_json},
        "urls.primaryName": "All Microservices (Unified)",
        dom_id: "#swagger-ui",
        deepLinking: true,
        persistAuthorization: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout"
      }});
    }};
  </script>
</body>
</html>"""
    return HTMLResponse(content=html)


@app.get("/redoc", include_in_schema=False)
async def redoc_ui():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{settings.PROJECT_NAME} - ReDoc",
    )


app.include_router(gateway.router)
