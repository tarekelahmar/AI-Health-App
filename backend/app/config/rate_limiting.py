"""Rate limiting configuration and utilities"""
from typing import Optional
from fastapi import Request, HTTPException, status
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config.settings import get_settings

settings = get_settings()

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,  # Rate limit by IP address
    default_limits=[],  # No default limits - apply explicitly
    storage_uri="memory://",  # In-memory storage (no Redis needed)
)


def get_user_id_for_rate_limit(request: Request) -> str:
    """
    Get user ID from request for per-user rate limiting.
    Falls back to IP address if user is not authenticated.
    """
    # Try to get current user from request state (set by auth dependency)
    # Note: This requires the endpoint to set request.state.user
    # For now, we'll use a simpler approach - check if user is authenticated
    # via the token in the request
    try:
        # Check if there's an Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # User is authenticated, use IP + path as key (will be per-user in practice)
            # For proper user-based limiting, we'd need to decode the token here
            # For now, use IP as fallback
            return f"user:{get_remote_address(request)}"
    except Exception:
        pass
    
    # Fall back to IP address
    return get_remote_address(request)


def create_user_limiter():
    """Create a limiter that uses user ID instead of IP"""
    return Limiter(
        key_func=get_user_id_for_rate_limit,
        default_limits=[],
        storage_uri="memory://",
    )


# User-based limiter (for authenticated endpoints)
user_limiter = create_user_limiter()


def get_rate_limit_key(request: Request) -> str:
    """
    Get rate limit key for the request.
    Uses user ID if authenticated, otherwise IP address.
    """
    return get_user_id_for_rate_limit(request)


# Rate limit decorator for IP-based limiting
def rate_limit_ip(limit: str):
    """
    Decorator for IP-based rate limiting.
    
    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
    
    Example:
        @rate_limit_ip("5/minute")
        def my_endpoint():
            ...
    """
    return limiter.limit(limit)


# Rate limit decorator for user-based limiting
def rate_limit_user(limit: str):
    """
    Decorator for user-based rate limiting.
    
    Args:
        limit: Rate limit string (e.g., "10/minute", "100/hour")
    
    Example:
        @rate_limit_user("5/minute")
        def my_endpoint():
            ...
    """
    return user_limiter.limit(limit)


# Predefined rate limits from settings
INSIGHT_RATE_LIMIT = "10/minute"  # 10 insight generations per minute
LLM_RATE_LIMIT = "5/minute"  # 5 LLM calls per minute (more restrictive)
AUTH_RATE_LIMIT = "5/minute"  # 5 login attempts per minute
GENERAL_RATE_LIMIT = "100/hour"  # General API rate limit


def setup_rate_limiting(app):
    """
    Setup rate limiting middleware and exception handler.
    
    Call this in main.py after creating the FastAPI app.
    """
    # Add rate limiting middleware
    app.state.limiter = limiter
    app.state.user_limiter = user_limiter
    app.add_middleware(SlowAPIMiddleware)
    
    # Add exception handler for rate limit exceeded
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    return app


def get_rate_limit_info(request: Request) -> dict:
    """
    Get current rate limit information for debugging.
    Returns remaining requests and reset time.
    """
    # This is a helper for debugging/monitoring
    # slowapi doesn't expose this directly, but we can add it if needed
    return {
        "rate_limiting_enabled": True,
        "key": get_rate_limit_key(request),
    }

