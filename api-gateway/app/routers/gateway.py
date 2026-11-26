from fastapi import APIRouter, Request
from app.clients import forward_request

router = APIRouter(tags=["API Gateway Proxy"])


@router.api_route(
    "/api/v1/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    include_in_schema=False,
)
async def proxy_api_v1(full_path: str, request: Request):
    return await forward_request(request)


@router.api_route(
    "/internal/{full_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    include_in_schema=False,
)
async def block_internal_routes(full_path: str, request: Request):
    return await forward_request(request)
