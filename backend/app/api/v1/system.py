"""
X7: System Status Endpoint

Expose GET /api/v1/system/status returning ENV_MODE, AUTH_MODE, PROVIDERS_ENABLED, SAFETY_STATUS.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.config.environment import get_env_mode, get_mode_config, is_production, is_staging, is_dev
from app.api.router_factory import make_v1_router
from app.api.auth_mode import get_request_user_id

router = make_v1_router(prefix="/api/v1/system", tags=["system"])
# Public (unauthenticated) router for liveness checks (CI/K8s/etc).
# Must not leak environment/auth posture details.
public_router = make_v1_router(prefix="/api/v1/system", tags=["system"], public=True)


class SystemStatusResponse(BaseModel):
    """System status response."""
    env_mode: str
    auth_mode: str
    providers_enabled: bool
    safety_status: str
    logging_level: str
    enable_llm: bool


class HealthzResponse(BaseModel):
    status: str


@public_router.get("/healthz", response_model=HealthzResponse)
def healthz(db: Session = Depends(get_db)):
    """
    Minimal liveness endpoint (no auth).
    
    Security posture:
    - Returns only "ok" (no ENV_MODE/AUTH_MODE leakage).
    - Used by CI smoke tests and typical deployment liveness probes.
    """
    try:
        # Minimal DB ping; if DB is unavailable, treat as unhealthy.
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="unhealthy")
    return HealthzResponse(status="ok")


@router.get("/status", response_model=SystemStatusResponse)
def get_system_status(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    """
    Get system status including environment mode, auth mode, providers, and safety.
    
    AUDIT FIX: Requires authentication to prevent security posture leakage.
    """
    env_mode = get_env_mode()
    config = get_mode_config()
    
    # Determine safety status
    if config["safety_strict"]:
        safety_status = "strict"
    else:
        safety_status = "relaxed"
    
    return SystemStatusResponse(
        env_mode=env_mode.value,
        auth_mode=config["auth_mode"],
        providers_enabled=config["providers_enabled"],
        safety_status=safety_status,
        logging_level=config["logging_level"],
        enable_llm=config["enable_llm"],
    )

