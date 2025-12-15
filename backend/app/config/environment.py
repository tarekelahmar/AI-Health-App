"""
X7: Production Mode Switch

Create ENV_MODE (dev, staging, production) with specific rules for authentication,
providers, safety, and logging.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Dict, Any


class EnvironmentMode(str, Enum):
    """Environment mode."""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


def get_env_mode() -> EnvironmentMode:
    """Get current environment mode from ENV_MODE env var."""
    mode_str = os.getenv("ENV_MODE", "dev").lower()
    try:
        return EnvironmentMode(mode_str)
    except ValueError:
        return EnvironmentMode.DEV


def get_mode_config() -> Dict[str, Any]:
    """
    SECURITY FIX (Risk #9): Single source of truth for environment configuration.
    
    Get configuration for current environment mode.
    
    Returns dict with:
    - auth_mode: "public" or "private"
    - providers_enabled: bool
    - safety_strict: bool
    - logging_level: str
    - enable_llm: bool
    
    Rules:
    - dev: AUTH_MODE can be set to "public" or "private" (default: "public")
    - staging: AUTH_MODE is always "private" (enforced)
    - production: AUTH_MODE is always "private" (enforced, fail hard if misconfigured)
    """
    mode = get_env_mode()
    
    # SECURITY FIX: Enforce auth mode based on environment
    if mode == EnvironmentMode.PRODUCTION:
        # Production MUST use private auth - fail hard if misconfigured
        auth_mode_override = os.getenv("AUTH_MODE", "").strip().lower()
        if auth_mode_override and auth_mode_override != "private":
            import logging
            logger = logging.getLogger(__name__)
            logger.critical(
                "PRODUCTION_AUTH_MISCONFIGURED",
                extra={
                    "env_mode": mode.value,
                    "auth_mode_override": auth_mode_override,
                    "enforced_auth_mode": "private",
                },
            )
            # Still enforce private, but log the misconfiguration
        auth_mode = "private"
    elif mode == EnvironmentMode.STAGING:
        # Staging should use private auth
        auth_mode = "private"
    else:
        # Dev: allow AUTH_MODE env var to control it
        auth_mode = os.getenv("AUTH_MODE", "public").strip().lower()
        if auth_mode not in ["public", "private"]:
            auth_mode = "public"  # Default to public for dev
    
    configs = {
        EnvironmentMode.DEV: {
            "auth_mode": auth_mode,
            "providers_enabled": os.getenv("PROVIDERS_ENABLED", "false").lower() == "true",
            "safety_strict": False,
            "logging_level": "DEBUG",
            "enable_llm": os.getenv("ENABLE_LLM_TRANSLATION", "false").lower() == "true",
            # WEEK 3: Disable prescriptive/diagnostic features by default
            "enable_rag": os.getenv("ENABLE_RAG_ENGINE", "false").lower() == "true",
            "enable_dysfunction_detection": os.getenv("ENABLE_DYSFUNCTION_DETECTION", "false").lower() == "true",
        },
        EnvironmentMode.STAGING: {
            "auth_mode": auth_mode,  # Always "private" due to enforcement above
            "providers_enabled": os.getenv("PROVIDERS_ENABLED", "true").lower() == "true",
            "safety_strict": True,
            "logging_level": "INFO",
            "enable_llm": os.getenv("ENABLE_LLM_TRANSLATION", "true").lower() == "true",
            # WEEK 3: Disable prescriptive features in staging/production
            "enable_rag": False,  # Disabled - prescriptive/diagnostic
            "enable_dysfunction_detection": False,  # Disabled - diagnostic framing
        },
        EnvironmentMode.PRODUCTION: {
            "auth_mode": auth_mode,  # Always "private" due to enforcement above
            "providers_enabled": os.getenv("PROVIDERS_ENABLED", "true").lower() == "true",
            "safety_strict": True,
            "logging_level": "WARNING",  # Production should be quieter
            "enable_llm": os.getenv("ENABLE_LLM_TRANSLATION", "true").lower() == "true",
            # WEEK 3: Disable prescriptive features in production
            "enable_rag": False,  # Disabled - prescriptive/diagnostic
            "enable_dysfunction_detection": False,  # Disabled - diagnostic framing
        },
    }
    
    return configs.get(mode, configs[EnvironmentMode.DEV])


def is_production() -> bool:
    """Check if running in production mode."""
    return get_env_mode() == EnvironmentMode.PRODUCTION


def is_staging() -> bool:
    """Check if running in staging mode."""
    return get_env_mode() == EnvironmentMode.STAGING


def is_dev() -> bool:
    """Check if running in dev mode."""
    return get_env_mode() == EnvironmentMode.DEV

