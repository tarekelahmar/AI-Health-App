from fastapi import APIRouter, Response, Depends, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from app.api.router_factory import make_v1_router
from app.api.auth_mode import get_request_user_id, is_private_mode
from app.config.environment import is_production, is_staging

# AUDIT FIX: Use make_v1_router and require auth in private mode
router = make_v1_router(prefix="/api/v1", tags=["observability"], public=False)

REQUESTS = Counter(
    "api_requests_total",
    "Total API requests",
    ["method", "path", "status"],
)

LATENCY = Histogram(
    "api_request_latency_seconds",
    "API request latency in seconds",
    ["method", "path"],
)


@router.get("/metrics")
def metrics(
    user_id: int = Depends(get_request_user_id),
):
    """
    Prometheus metrics endpoint.
    
    AUDIT FIX: Requires authentication in private mode.
    In production/staging, this endpoint should be restricted to internal monitoring.
    """
    # AUDIT FIX: In production/staging, additional IP allowlist could be added here
    # For now, require authentication
    if is_private_mode():
        # Already authenticated via get_request_user_id
        pass
    
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

