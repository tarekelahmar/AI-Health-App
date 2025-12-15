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
    Get configuration for current environment mode.
    
    Returns dict with:
    - auth_mode: "public" or "private"
    - providers_enabled: bool
    - safety_strict: bool
    - logging_level: str
    - enable_llm: bool
    """
    mode = get_env_mode()
    
    configs = {
        EnvironmentMode.DEV: {
            "auth_mode": os.getenv("AUTH_MODE", "public"),
            "providers_enabled": os.getenv("PROVIDERS_ENABLED", "false").lower() == "true",
            "safety_strict": False,
            "logging_level": "DEBUG",
            "enable_llm": os.getenv("ENABLE_LLM_TRANSLATION", "false").lower() == "true",
        },
        EnvironmentMode.STAGING: {
            "auth_mode": "private",  # Staging should use auth
            "providers_enabled": os.getenv("PROVIDERS_ENABLED", "true").lower() == "true",
            "safety_strict": True,
            "logging_level": "INFO",
            "enable_llm": os.getenv("ENABLE_LLM_TRANSLATION", "true").lower() == "true",
        },
        EnvironmentMode.PRODUCTION: {
            "auth_mode": "private",  # Production must use auth
            "providers_enabled": os.getenv("PROVIDERS_ENABLED", "true").lower() == "true",
            "safety_strict": True,
            "logging_level": "WARNING",  # Production should be quieter
            "enable_llm": os.getenv("ENABLE_LLM_TRANSLATION", "true").lower() == "true",
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

