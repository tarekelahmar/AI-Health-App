from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Sequence

from app.integrations.base import (
    AuthToken,
    HealthDataPoint,
    HealthDataProvider,
    RateLimitConfig,
)
from app.domain.metrics.registry import METRIC_REGISTRY, get_metric_spec


class WhoopProvider(HealthDataProvider):
    """
    WHOOP implementation of the HealthDataProvider interface.

    Phase 1.2 notes:
    - This class is intentionally thin and *reuses* the existing WHOOP adapter
      and token storage logic rather than duplicating the OAuth or ingestion
      pipelines.
    - For now, async methods delegate to the existing synchronous adapter;
      call sites should treat this as a blocking integration until we
      introduce non-blocking HTTP clients in a later phase.
    - The production sync / ingestion path still flows through
      ProviderSyncService + WhoopAdapter to avoid any behavior changes.
      This provider is primarily used for discovery and future multi-provider
      wiring.
    """

    name = "whoop"

    def __init__(self) -> None:
        # No heavy wiring in __init__; we keep construction cheap so that the
        # provider health endpoint can safely instantiate providers.
        pass

    async def authenticate(self, auth_payload: Dict) -> AuthToken:
        """
        Delegate to the existing WHOOP OAuth flow.

        Phase 1.2 intentionally does *not* rewire the public OAuth endpoints
        to this abstraction to avoid changing request/response contracts.
        Callers should continue to use the /providers/whoop endpoints, which
        already wrap the underlying adapter and token repository.
        """
        raise NotImplementedError(
            "WhoopProvider.authenticate is not wired into the OAuth flow yet. "
            "Use the existing /api/v1/providers/whoop endpoints."
        )

    async def fetch_data(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metrics: Sequence[str],
    ) -> List[HealthDataPoint]:
        """
        Experimental WHOOP data fetch wrapper.

        For now, this delegates to the existing WhoopAdapter.fetch_and_normalize
        implementation and converts NormalizedPoint objects into detached
        HealthDataPoint ORM instances.

        IMPORTANT:
        - This method does *not* persist any rows.
        - The primary ingestion path continues to be ProviderSyncService.sync_whoop.
        - This is exposed to make future multi-provider ingestion structurally easy.
        """
        # Local import to avoid creating DB engine at import time and to keep
        # this abstraction decoupled from the rest of the app where possible.
        from app.core.database import SessionLocal  # type: ignore
        from app.providers.whoop.whoop_adapter import WhoopAdapter

        # Validate metric keys against the canonical registry.
        requested_specs = self._validate_metric_keys(metrics)
        requested_keys = {s.key for s in requested_specs}

        db = SessionLocal()
        try:
            adapter = WhoopAdapter(db)
            # The existing adapter accepts a "since" parameter; for now we pass
            # the requested start time and rely on the adapter's internal
            # windowing (limit) semantics. We then filter to [start, end).
            normalized_points = adapter.fetch_and_normalize(user_id=user_id, since=start)
        finally:
            db.close()

        results: List[HealthDataPoint] = []
        for p in normalized_points:
            metric_key = p.metric_type
            # Filter to requested metrics only.
            if metric_key not in requested_keys:
                continue

            ts = p.timestamp
            if ts < start or ts >= end:
                continue

            spec = get_metric_spec(metric_key)
            lo, hi = spec.valid_range
            value = float(p.value)

            # Provider-level guardrail: discard obviously invalid values
            # before they hit downstream pipelines. The main ingestion
            # path still enforces hard invariants on top of this.
            if not (lo <= value <= hi):
                continue

            # Construct a detached ORM instance. It is the caller's
            # responsibility to attach and persist if desired.
            results.append(
                HealthDataPoint(
                    user_id=user_id,
                    metric_type=metric_key,  # type: ignore[arg-type]
                    value=value,
                    unit=p.unit,
                    timestamp=ts,
                    source=p.source,
                )
            )

        # Ensure deterministic ordering by timestamp.
        results.sort(key=lambda r: r.timestamp)
        return results

    def get_supported_metrics(self) -> List[str]:
        """
        Return the subset of canonical metrics that WHOOP actually produces
        in the current integration.
        """
        # WHOOP adapter currently maps:
        # - sleep_duration
        # - resting_hr
        # - hrv_rmssd
        supported = []
        for key in ("sleep_duration", "resting_hr", "hrv_rmssd"):
            if key in METRIC_REGISTRY:
                supported.append(key)
        return supported

    def get_rate_limits(self) -> RateLimitConfig:
        # Conservative defaults; tune once we have measured provider behavior.
        return RateLimitConfig(requests_per_minute=30, burst_size=60)


