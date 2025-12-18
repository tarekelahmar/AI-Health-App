from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from app.domain.metrics.registry import MetricSpec, get_metric_spec

# IMPORTANT:
# Reuse the existing ORM / domain HealthDataPoint model rather than recreating the DB table.
# Import the domain model where it actually lives.
try:
    # Actual model location in this codebase.
    from app.domain.models.health_data_point import HealthDataPoint  # type: ignore[no-redef]
except ImportError:
    # Fallback: define a lightweight protocol-like dataclass for non-DB uses.
    # If you hit this path, fix the import above to the real model and remove this.
    from dataclasses import dataclass as _dc_dataclass

    @_dc_dataclass
    class HealthDataPoint:  # type: ignore[no-redef]
        user_id: int
        metric_key: str
        timestamp: datetime
        value: float
        source: str
        raw: Optional[dict] = None


@dataclass(frozen=True)
class AuthToken:
    access_token: str
    refresh_token: Optional[str]
    expires_at: Optional[datetime]
    scope: Optional[str] = None
    raw: Optional[Dict] = None


@dataclass(frozen=True)
class RateLimitConfig:
    requests_per_minute: int
    burst_size: int
    # Additional fields can be added later (daily caps, etc.)


class HealthDataProvider(ABC):
    """
    Abstract base class for all health data providers.

    Implementations MUST:
    - Respect rate limits (best-effort).
    - Map provider-native metrics to the canonical METRIC_REGISTRY.
    - Only return values within the MetricSpec.valid_range; out-of-range values
      should be filtered or explicitly flagged upstream.
    """

    name: str  # Short provider key, e.g. "whoop", "oura"

    @abstractmethod
    async def authenticate(self, auth_payload: Dict) -> AuthToken:
        """
        Perform provider-specific authentication / token exchange.

        auth_payload is whatever the frontend / OAuth callback supplies
        (e.g. auth_code, redirect_uri, etc.).
        """
        raise NotImplementedError

    @abstractmethod
    async def fetch_data(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metrics: Sequence[str],
    ) -> List[HealthDataPoint]:
        """
        Fetch health data for a given user in [start, end) for the requested canonical metrics.

        - metrics are keys in METRIC_REGISTRY (e.g. "sleep_duration", "hrv_rmssd").
        - Implementations are responsible for mapping provider-native metrics to these keys.
        - Returned data MUST be:
            * Sorted by timestamp (ascending).
            * Within MetricSpec.valid_range (filter out clearly broken values).
        """
        raise NotImplementedError

    @abstractmethod
    def get_supported_metrics(self) -> List[str]:
        """
        Returns canonical metric keys supported by this provider.
        """
        raise NotImplementedError

    @abstractmethod
    def get_rate_limits(self) -> RateLimitConfig:
        """
        Returns rate limit configuration for this provider.
        """
        raise NotImplementedError

    # Optional helper for input validation that concrete providers can use.
    def _validate_metric_keys(self, metrics: Sequence[str]) -> List[MetricSpec]:
        specs: List[MetricSpec] = []
        for m in metrics:
            try:
                specs.append(get_metric_spec(m))
            except KeyError as e:
                # Surface provider-side correctly: unknown canonical metric requested
                raise ValueError(f"Unsupported metric for {self.name}: {m}") from e
        return specs


