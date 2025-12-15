from __future__ import annotations

from fastapi import APIRouter
from app.api.auth_mode import get_auth_mode

auth_mode_router = APIRouter(prefix="/api/v1/auth-mode", tags=["auth"])


@auth_mode_router.get("")
def auth_mode():
    return {"AUTH_MODE": get_auth_mode()}

