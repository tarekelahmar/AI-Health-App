from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Sequence

from app.integrations.base import (
    AuthToken,
    HealthDataPoint,
    HealthDataProvider,
    RateLimitConfig,
)


class OuraProvider(HealthDataProvider):
    """
    Stub implementation for Oura integration.

    Phase 1.2 intentionally *does not* implement the full Oura flow – all
    entrypoints fail closed with NotImplementedError so there is no silent
    fallback or partial ingestion.
    """

    name = "oura"

    async def authenticate(self, auth_payload: Dict) -> AuthToken:
        raise NotImplementedError("OuraProvider.authenticate is not implemented yet")

    async def fetch_data(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metrics: Sequence[str],
    ) -> List[HealthDataPoint]:
        raise NotImplementedError("OuraProvider.fetch_data is not implemented yet")

    def get_supported_metrics(self) -> List[str]:
        # No metrics are wired yet; implementation will be added in a later phase.
        return []

    def get_rate_limits(self) -> RateLimitConfig:
        # Zeroed limits clearly communicate "disabled" state.
        return RateLimitConfig(requests_per_minute=0, burst_size=0)


