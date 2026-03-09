from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Sequence

from app.integrations.base import (
    AuthToken,
    HealthDataPoint,
    HealthDataProvider,
    RateLimitConfig,
)


class AppleHealthProvider(HealthDataProvider):
    """
    Stub implementation for Apple Health integration.

    Phase 1.2 only defines the interface; concrete implementation will be
    added in a later phase once native integrations are ready.
    """

    name = "apple_health"

    async def authenticate(self, auth_payload: Dict) -> AuthToken:
        raise NotImplementedError("AppleHealthProvider.authenticate is not implemented yet")

    async def fetch_data(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metrics: Sequence[str],
    ) -> List[HealthDataPoint]:
        raise NotImplementedError("AppleHealthProvider.fetch_data is not implemented yet")

    def get_supported_metrics(self) -> List[str]:
        # No metrics are wired yet; implementation will be added in a later phase.
        return []

    def get_rate_limits(self) -> RateLimitConfig:
        # Zeroed limits clearly communicate "disabled" state.
        return RateLimitConfig(requests_per_minute=0, burst_size=0)


