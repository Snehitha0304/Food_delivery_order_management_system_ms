from datetime import datetime, timezone
from fastapi import APIRouter
from app.clients import check_all_services_health

router = APIRouter(tags=["Gateway Health"])


@router.get("/health", summary="Aggregated health check across all microservices")
async def gateway_health():
    report = await check_all_services_health()
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    return report


@router.get("/api/v1/health", summary="Aggregated health check (v1)")
async def gateway_health_v1():
    report = await check_all_services_health()
    report["timestamp"] = datetime.now(timezone.utc).isoformat()
    return report
