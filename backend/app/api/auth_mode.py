from __future__ import annotations

import os
from typing import Optional

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer

# SECURITY FIX (Risk #9): Single source of truth for auth mode
from app.config.environment import get_mode_config

# IMPORTANT:
# We do NOT import get_current_user directly here because many projects
# have it as "hard-required" (auto_error=True). We implement an optional
# resolver that can be used in both modes safely.
#
# If you already have JWT verification utilities, wire them in below
# by replacing `_get_user_from_token(token)` implementation.

# If your tokenUrl differs, update it here:
oauth2_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_auth_mode() -> str:
    """
    SECURITY FIX (Risk #9): Single source of truth for auth mode.
    Uses environment mode config, which enforces:
    - dev: can be public or private (from AUTH_MODE env var)
    - staging: always private
    - production: always private
    
    Falls back to AUTH_MODE env var if environment config not available.
    """
    try:
        config = get_mode_config()
        return config["auth_mode"]
    except Exception:
        # Fallback to direct env var read (for backward compatibility)
        return os.getenv("AUTH_MODE", "public").strip().lower()


def is_private_mode() -> bool:
    return get_auth_mode() == "private"


# --- Replace this with your existing token->user decode logic ---
# You likely already have something in app/config/security.py such as:
#   - decode_access_token(token)
#   - get_user_by_id(...)
#   - verify_jwt(...)
# Hook those in here.
def _get_user_from_token(token: str):
    """
    Return a User-like object with .id if token is valid, else None.
    """
    try:
        # Try to reuse your existing implementation if present:
        from app.config.security import get_current_user  # type: ignore
        # We can't call it directly because it expects Depends injection.
        # So: fall back to "optional" decode path below if you have helpers.
    except Exception:
        pass

    # Optional integration path:
    # If you have decode_access_token() -> dict with "sub" = user_id
    try:
        import jwt
        from app.config.settings import get_settings
        from app.domain.repositories.user_repository import UserRepository  # type: ignore
        from app.core.database import SessionLocal  # type: ignore

        settings = get_settings()
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload.get("sub"))
        db = SessionLocal()
        try:
            repo = UserRepository(db)
            user = repo.get_by_id(user_id)
            return user
        finally:
            db.close()
    except Exception:
        # If JWT decode fails, return None
        return None


async def get_current_user_optional(token: Optional[str] = Depends(oauth2_optional)):
    """
    In public mode: returns None always (auth not required).
    In private mode: returns user if token valid; else raises 401.
    """
    if not is_private_mode():
        return None

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    user = _get_user_from_token(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    # must have .id
    if not getattr(user, "id", None):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid user")

    return user


def get_request_user_id(
    request: Request,
    user_id: Optional[int] = Query(default=None),
    current_user=Depends(get_current_user_optional),
) -> int:
    """
    Unified "who is this request for?" dependency.

    - public mode: requires ?user_id=...
    - private mode: ignores ?user_id=... and uses current_user.id
    """
    if is_private_mode():
        # current_user_optional() already enforced auth in private mode
        return int(current_user.id)

    # public mode
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing required query param: user_id (AUTH_MODE=public)",
        )
    return int(user_id)

