"""
Demo/synthetic data provider for testing and development.

Implements the same interface as real providers but generates synthetic data
using the HealthDataFactory. This provider is *not* automatically wired into
production flows; registration is gated on ENV_MODE == 'demo'.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence
import os

from app.integrations.base import (
    AuthToken,
    HealthDataPoint,
    HealthDataProvider,
    RateLimitConfig,
)
from app.integrations.data_factory import HealthDataFactory, PersonalProfile
from app.integrations.scenarios import SCENARIOS
from app.domain.metrics.registry import METRIC_REGISTRY


class DemoProvider(HealthDataProvider):
    """Synthetic data provider for testing."""

    name = "demo"

    def __init__(
        self,
        scenario: str = "healthy_baseline",
        seed: Optional[int] = None,
        profile: Optional[PersonalProfile] = None,
    ) -> None:
        self.scenario = scenario
        self.factory = HealthDataFactory(
            profile=profile,
            seed=seed or 42,
        )
        self.scenario_schedule = SCENARIOS.get(scenario, {})

    def get_supported_metrics(self) -> List[str]:
        """Return metrics this provider can supply (canonical keys)."""
        # Constrain to keys that exist in the registry to avoid silent drops.
        supported = [
            key
            for key in [
                "sleep_duration",
                "sleep_efficiency",
                "hrv_rmssd",
                "resting_hr",
                "respiratory_rate",
                "skin_temp_deviation",
                "spo2",
            ]
            if key in METRIC_REGISTRY
        ]
        # For now, METRIC_REGISTRY may not have all extra signals; we always
        # include the core sleep/recovery metrics if present.
        return supported or [k for k in ("sleep_duration", "hrv_rmssd", "resting_hr") if k in METRIC_REGISTRY]

    def get_rate_limits(self) -> RateLimitConfig:
        # Extremely generous limits; demo data is local and not rate-limited.
        return RateLimitConfig(requests_per_minute=1000, burst_size=2000)

    async def authenticate(self, auth_payload: Dict) -> AuthToken:
        """
        No-op auth for demo provider.

        Returns a synthetic token payload so that the interface matches
        real providers without touching production auth flows.
        """
        return AuthToken(
            access_token="demo_token",
            refresh_token=None,
            expires_at=None,
            scope="demo",
            raw={"mode": "demo", "env": os.getenv("ENV_MODE", "dev")},
        )

    async def fetch_data(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metrics: Sequence[str],
    ) -> List[HealthDataPoint]:
        """Generate synthetic data for the requested range."""

        # Use requested metric keys if provided, fall back to supported set.
        requested_metrics = list(metrics) or self.get_supported_metrics()

        # Daily cadence: inclusive of end date.
        days = max(1, (end.date() - start.date()).days + 1)
        raw_data = self.factory.generate_range(
            start_date=datetime.combine(start.date(), datetime.min.time()),
            days=days,
            scenario_schedule=self.scenario_schedule,
        )

        points: List[HealthDataPoint] = []

        for day_data in raw_data:
            date_str = day_data.get("date")
            if not date_str:
                continue
            # Use naive UTC-style datetime; loop runner uses UTC-naive timestamps.
            timestamp = datetime.fromisoformat(date_str)

            for metric_key, value in day_data.items():
                if metric_key == "date":
                    continue
                if metric_key not in requested_metrics:
                    continue

                # Map units to something sensible; for now we keep units
                # simple and aligned with how registry describes them.
                unit = None
                if metric_key == "sleep_duration":
                    # Factory emits hours; store hours for demo consistency.
                    unit = "hours"
                elif metric_key in {"hrv_rmssd"}:
                    unit = "ms"
                elif metric_key in {"resting_hr"}:
                    unit = "bpm"
                elif metric_key in {"sleep_efficiency"}:
                    unit = "ratio"
                elif metric_key == "respiratory_rate":
                    unit = "breaths_per_minute"
                elif metric_key == "skin_temp_deviation":
                    unit = "celsius_delta"
                elif metric_key == "spo2":
                    unit = "percent"
                else:
                    unit = "unit"

                points.append(
                    HealthDataPoint(
                        user_id=user_id,
                        metric_type=metric_key,  # type: ignore[arg-type]
                        value=float(value),
                        unit=unit,
                        timestamp=timestamp,
                        source="demo",
                    )
                )

        return points


