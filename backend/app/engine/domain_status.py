"""
Domain-level status / silence classification (metadata only).

Purpose
-------
Provide a deterministic, conservative answer to:
  "Does the system currently have something meaningful to say about this domain,
   or is silence intentional?"

Non-goals (intentional)
-----------------------
- No analytics, thresholds, heuristics, confidence logic, or grading
- No ranking/comparison across domains
- No suppression/elevation changes
- No causality, diagnosis, or recommendations

This module is safe to use across loop runner, narratives, trust, and audit plumbing.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Dict, Iterable, Optional, Sequence, Set

from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.domain.health_domains import HEALTH_DOMAINS, HealthDomainKey, domain_for_signal
from app.domain.models.baseline import Baseline
from app.domain.models.health_data_point import HealthDataPoint


class DomainStatus(str, Enum):
    """
    Canonical domain status values (EXACT set required).
    """

    NO_DATA = "NO_DATA"
    BASELINE_BUILDING = "BASELINE_BUILDING"
    NO_SIGNAL_DETECTED = "NO_SIGNAL_DETECTED"
    SIGNAL_DETECTED = "SIGNAL_DETECTED"


def _safe_insight_domain_key(obj: object) -> Optional[HealthDomainKey]:
    """
    Best-effort extraction of domain_key from an Insight-like object.

    We only read existing fields; we do not infer probabilistically.
    """
    meta = getattr(obj, "metadata_json", None)
    if meta:
        try:
            if isinstance(meta, str):
                meta_obj = json.loads(meta)
            elif isinstance(meta, dict):
                meta_obj = meta
            else:
                meta_obj = {}
        except Exception:
            meta_obj = {}

        raw = meta_obj.get("domain_key")
        if isinstance(raw, str) and raw:
            try:
                return HealthDomainKey(raw)
            except Exception:
                return None

        mk = meta_obj.get("metric_key")
        if isinstance(mk, str) and mk:
            return domain_for_signal(mk)

    # Fallback: some insight-like objects may have metric_key directly
    mk = getattr(obj, "metric_key", None)
    if isinstance(mk, str) and mk:
        return domain_for_signal(mk)
    return None


def _domains_from_surfaced_insights(surfaced_insights: Optional[Sequence[object]]) -> Set[HealthDomainKey]:
    if not surfaced_insights:
        return set()
    out: Set[HealthDomainKey] = set()
    for it in surfaced_insights:
        dk = _safe_insight_domain_key(it)
        if dk:
            out.add(dk)
    return out


def compute_domain_status(
    db: Session,
    *,
    user_id: int,
    domain_key: HealthDomainKey,
    surfaced_insights: Optional[Sequence[object]] = None,
) -> DomainStatus:
    """
    Deterministically compute a domain status for a user.

    Inputs are limited to existing primitives:
    - DomainKey
    - domain's canonical signals
    - baseline availability for those signals
    - surfaced insights (post-suppression) (optional)

    Rules (conservative, ordered):
    1) If no signals present -> NO_DATA
    2) Else if baseline missing for relevant signals -> BASELINE_BUILDING
    3) Else if zero surfaced insights for domain -> NO_SIGNAL_DETECTED
    4) Else -> SIGNAL_DETECTED

    Backward compatibility:
    - Any unexpected errors default to NO_DATA (safe, conservative).
    """
    try:
        signals = HEALTH_DOMAINS[domain_key].signals

        # Signals present = at least one data point for any signal in this domain
        present_rows = (
            db.query(distinct(HealthDataPoint.metric_type))
            .filter(
                HealthDataPoint.user_id == user_id,
                HealthDataPoint.metric_type.in_(list(signals)),
            )
            .all()
        )
        present_signals = {r[0] for r in present_rows if r and isinstance(r[0], str)}

        if not present_signals:
            return DomainStatus.NO_DATA

        # Baseline established = baseline exists for all present signals (conservative)
        baseline_rows = (
            db.query(distinct(Baseline.metric_type))
            .filter(
                Baseline.user_id == user_id,
                Baseline.metric_type.in_(list(present_signals)),
            )
            .all()
        )
        baseline_signals = {r[0] for r in baseline_rows if r and isinstance(r[0], str)}
        missing_baselines = present_signals - baseline_signals
        if missing_baselines:
            return DomainStatus.BASELINE_BUILDING

        surfaced_domains = _domains_from_surfaced_insights(surfaced_insights)
        if domain_key not in surfaced_domains:
            return DomainStatus.NO_SIGNAL_DETECTED

        return DomainStatus.SIGNAL_DETECTED
    except Exception:
        return DomainStatus.NO_DATA


def compute_domain_statuses(
    db: Session,
    *,
    user_id: int,
    surfaced_insights: Optional[Sequence[object]] = None,
) -> Dict[HealthDomainKey, DomainStatus]:
    """
    Compute statuses for all canonical domains.

    Output is keyed by HealthDomainKey (no ranking; stable iteration order).
    """
    out: Dict[HealthDomainKey, DomainStatus] = {}
    for dk in HEALTH_DOMAINS.keys():
        out[dk] = compute_domain_status(db, user_id=user_id, domain_key=dk, surfaced_insights=surfaced_insights)
    return out


