"""
Concrete provider implementations and registration.

Importing this module registers all known providers with the global registry.
This keeps wiring explicit and avoids dynamic import magic.
"""

from __future__ import annotations

import os

from app.integrations.registry import register_provider
from app.integrations.providers.whoop_provider import WhoopProvider

# Register WHOOP (current production provider).
register_provider(WhoopProvider.name, WhoopProvider)

# Stubs for future providers – registered only if import/initialisation succeeds.
try:  # pragma: no cover - defensive, exercised indirectly via health endpoint
    from app.integrations.providers.oura_provider import OuraProvider

    register_provider(OuraProvider.name, OuraProvider)
except Exception:
    # Safe to ignore until implemented.
    pass

try:  # pragma: no cover - defensive, exercised indirectly via health endpoint
    from app.integrations.providers.apple_health_provider import AppleHealthProvider

    register_provider(AppleHealthProvider.name, AppleHealthProvider)
except Exception:
    # Safe to ignore until implemented.
    pass

# Demo provider is only registered in explicit demo environments to avoid
# accidental production use. ENV_MODE is already used throughout the app.
try:  # pragma: no cover - exercised via manual demo flows
    from app.integrations.providers.demo import DemoProvider

    if os.getenv("ENV_MODE", "").lower() == "demo":
        register_provider(DemoProvider.name, DemoProvider)
except Exception:
    # Safe to ignore if demo provider or ENV not configured.
    pass

