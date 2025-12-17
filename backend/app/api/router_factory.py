from __future__ import annotations

from fastapi import APIRouter, Depends
from typing import Optional

from app.api.auth_mode import get_auth_mode, is_private_mode, get_request_user_id


def make_v1_router(prefix: str, tags: list[str], *, public: bool = False) -> APIRouter:
    """
    Central router factory.
    
    AUDIT FIX: Actually enforces auth at router level in private mode.
    
    - If AUTH_MODE=public -> no auth dependencies (for dev/testing)
    - If AUTH_MODE=private -> router-level dependency enforces auth
    - public=True means: always public even in private mode (health checks, etc)
    """
    router = APIRouter(prefix=prefix, tags=tags)
    
    # AUDIT FIX: Actually enforce auth at router level in private mode
    if not public and is_private_mode():
        # Add router-level dependency that enforces authentication
        # This ensures all endpoints in this router require auth
        router.dependencies.append(Depends(get_request_user_id))
    
    return router

