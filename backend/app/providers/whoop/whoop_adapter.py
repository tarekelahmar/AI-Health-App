from __future__ import annotations

import os
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.providers.base import ProviderAdapter, NormalizedPoint
from app.providers.whoop.whoop_oauth import (
    build_whoop_authorize_url,
    exchange_code_for_token,
    refresh_token,
    compute_expires_at,
)
from app.providers.whoop.whoop_client import WhoopClient
from app.domain.metric_registry import get_metric_spec
from app.domain.repositories.provider_token_repository import ProviderTokenRepository

logger = logging.getLogger(__name__)


def _parse_rfc3339(ts: str) -> datetime:
    # WHOOP returns Z timestamps; Python fromisoformat doesn't accept Z on 3.9.
    # Minimal safe parse.
    # Example: "2025-01-01T12:34:56Z"
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts).replace(tzinfo=None)


class WhoopAdapter(ProviderAdapter):
    provider_name = "whoop"

    def __init__(self, db: Session):
        self.db = db
        self.token_repo = ProviderTokenRepository(db)

        self.client_id = os.getenv("WHOOP_CLIENT_ID", "")
        self.client_secret = os.getenv("WHOOP_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("WHOOP_REDIRECT_URI", "http://localhost:8000/api/v1/providers/whoop/callback")
        self.scope = os.getenv("WHOOP_SCOPE", "read:recovery read:sleep read:cycles")

        # Safety: Log warning if credentials are missing
        if not self.client_id or not self.client_secret or self.client_id == "__NOT_SET__" or self.client_secret == "__NOT_SET__":
            logger.warning(
                "WHOOP_CLIENT_ID or WHOOP_CLIENT_SECRET not set. "
                "WHOOP OAuth and data sync will be disabled. "
                "Set these in .env.local to enable WHOOP integration."
            )

    def build_authorize_url(self, state: str) -> str:
        # Safety: Refuse OAuth if credentials missing
        if not self.client_id or self.client_id == "__NOT_SET__":
            logger.error("WHOOP_CLIENT_ID not set. Cannot initiate OAuth flow.")
            raise RuntimeError("WHOOP_CLIENT_ID not set. Please configure WHOOP credentials in .env.local")
        if not self.client_secret or self.client_secret == "__NOT_SET__":
            logger.error("WHOOP_CLIENT_SECRET not set. Cannot initiate OAuth flow.")
            raise RuntimeError("WHOOP_CLIENT_SECRET not set. Please configure WHOOP credentials in .env.local")
        return build_whoop_authorize_url(self.client_id, self.redirect_uri, state, self.scope)

    def exchange_code_for_token(self, code: str, redirect_uri: str) -> Dict[str, Any]:
        # Safety: Refuse token exchange if credentials missing
        if not self.client_id or self.client_id == "__NOT_SET__":
            logger.error("WHOOP_CLIENT_ID not set. Cannot exchange OAuth code for token.")
            raise RuntimeError("WHOOP_CLIENT_ID not set. Please configure WHOOP credentials in .env.local")
        if not self.client_secret or self.client_secret == "__NOT_SET__":
            logger.error("WHOOP_CLIENT_SECRET not set. Cannot exchange OAuth code for token.")
            raise RuntimeError("WHOOP_CLIENT_SECRET not set. Please configure WHOOP credentials in .env.local")
        return exchange_code_for_token(self.client_id, self.client_secret, code, redirect_uri)

    def refresh_access_token_if_needed(self, user_id: int) -> None:
        token = self.token_repo.get(user_id=user_id, provider=self.provider_name)
        if not token:
            return
        if token.expires_at and token.expires_at <= datetime.utcnow():
            if not token.refresh_token:
                logger.warning(f"Token expired for user_id={user_id} but no refresh_token available")
                return
            # Safety: Refuse refresh if credentials missing
            if not self.client_id or self.client_id == "__NOT_SET__" or not self.client_secret or self.client_secret == "__NOT_SET__":
                logger.error(f"Cannot refresh token for user_id={user_id}: WHOOP credentials not set")
                return
            refreshed = refresh_token(self.client_id, self.client_secret, token.refresh_token)
            self.token_repo.upsert(
                user_id=user_id,
                provider=self.provider_name,
                access_token=refreshed.get("access_token"),
                refresh_token=refreshed.get("refresh_token", token.refresh_token),
                token_type=refreshed.get("token_type"),
                scope=refreshed.get("scope"),
                expires_at=compute_expires_at(refreshed.get("expires_in")),
            )

    def _require_access_token(self, user_id: int) -> str:
        token = self.token_repo.get(user_id=user_id, provider=self.provider_name)
        if not token:
            raise RuntimeError("WHOOP not connected for this user")
        return token.access_token

    def fetch_and_normalize(self, user_id: int, since: Optional[datetime] = None) -> List[NormalizedPoint]:
        # Safety: Ensure credentials are set before attempting to fetch data
        if not self.client_id or self.client_id == "__NOT_SET__" or not self.client_secret or self.client_secret == "__NOT_SET__":
            logger.error(f"Cannot fetch WHOOP data for user_id={user_id}: credentials not configured")
            raise RuntimeError("WHOOP credentials not configured. Cannot fetch data.")
        
        self.refresh_access_token_if_needed(user_id=user_id)
        access_token = self._require_access_token(user_id)
        client = WhoopClient(access_token)

        points: List[NormalizedPoint] = []

        # ---- SLEEP ----
        # We'll map:
        # - sleep_duration_minutes (WHOOP: sleep totals are often in milliseconds/seconds depending on endpoint)
        # - resting_hr (if present)
        # - hrv_rmssd (if present; WHOOP uses "rmssd" sometimes under recovery)
        sleeps = client.get_sleep(since=since, limit=50)
        for rec in sleeps:
            # WHOOP sleep records commonly contain "score" and "sleep" blocks.
            # We defensively extract if present.
            end_ts = rec.get("end") or rec.get("end_time") or rec.get("end_time_utc")
            if not end_ts:
                continue
            ts = _parse_rfc3339(end_ts)

            sleep_block = rec.get("sleep", {}) or {}
            score_block = rec.get("score", {}) or {}

            # duration: WHOOP sometimes provides milliseconds
            duration_ms = sleep_block.get("total_in_bed_time_ms") or sleep_block.get("total_sleep_time_ms")
            duration_min = None
            if duration_ms is not None:
                duration_min = float(duration_ms) / 60000.0

            if duration_min is not None:
                spec = get_metric_spec("sleep_duration")
                points.append(
                    NormalizedPoint(
                        metric_type="sleep_duration",
                        value=float(duration_min),
                        unit=spec.unit,
                        timestamp=ts,
                        source="whoop",
                        metadata={"whoop_sleep_id": rec.get("id")},
                    )
                )

        # ---- RECOVERY ----
        recoveries = client.get_recovery(since=since, limit=50)
        for rec in recoveries:
            ts_raw = rec.get("timestamp") or rec.get("created_at") or rec.get("updated_at")
            if not ts_raw:
                continue
            ts = _parse_rfc3339(ts_raw)

            # WHOOP recovery typically includes:
            # - resting_heart_rate
            # - hrv_rmssd_milli or hrv_rmssd
            # - recovery_score (0-100)
            rhr = rec.get("resting_heart_rate")
            rmssd = rec.get("hrv_rmssd_milli") or rec.get("hrv_rmssd")

            if rhr is not None:
                spec = get_metric_spec("resting_hr")
                points.append(
                    NormalizedPoint(
                        metric_type="resting_hr",
                        value=float(rhr),
                        unit=spec.unit,
                        timestamp=ts,
                        source="whoop",
                        metadata={"whoop_recovery_id": rec.get("id")},
                    )
                )
            if rmssd is not None:
                spec = get_metric_spec("hrv_rmssd")
                points.append(
                    NormalizedPoint(
                        metric_type="hrv_rmssd",
                        value=float(rmssd),
                        unit=spec.unit,
                        timestamp=ts,
                        source="whoop",
                        metadata={"whoop_recovery_id": rec.get("id")},
                    )
                )

        return points

