"""
Application configuration - Backward compatibility layer

This module re-exports settings from app.config to maintain backward compatibility.
All new code should import directly from app.config.settings.
"""

from app.config.settings import (
    get_settings,
    Settings,
    validate_config,
)

# Re-export for backward compatibility
__all__ = [
    "get_settings",
    "Settings",
    "validate_config",
]
