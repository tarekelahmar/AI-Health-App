"""
Provider integrations package.

Phase 1.2:
- Defines a shared abstraction for health data providers.
- Wires concrete providers (WHOOP, future Oura / Apple Health) into a simple
  in-memory registry for discovery and governance/health checks.

Importing this package is side-effectful: it ensures providers are registered
with the registry via the providers subpackage.
"""

from __future__ import annotations

# Ensure provider classes are imported so their registration side effects run.
from app.integrations import registry  # noqa: F401
from app.integrations import providers  # noqa: F401


