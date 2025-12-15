from __future__ import annotations

from fastapi import APIRouter

from app.api.auth_mode import get_auth_mode


def make_v1_router(prefix: str, tags: list[str], *, public: bool = False) -> APIRouter:
    """
    Central router factory.
    - If AUTH_MODE=public -> no auth dependencies anywhere by default.
    - If AUTH_MODE=private -> routers are still created, but endpoints should
      rely on get_request_user_id (which enforces auth).
    - public=True means: always public even in private mode (health checks, metrics, etc).
    """
    # We intentionally do NOT attach Depends(get_current_user) at router-level
    # because we want a single consistent mechanism (get_request_user_id) that:
    #   - enforces auth in private mode
    #   - enforces user_id in public mode
    #
    # For true always-public routers, you can still use public=True and skip user id deps.
    return APIRouter(prefix=prefix, tags=tags)

