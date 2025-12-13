from dataclasses import dataclass

from typing import Optional, Tuple, Dict


@dataclass(frozen=True)
class CanonicalMetric:
    key: str                     # internal identifier
    domain: str                  # sleep, recovery, metabolic
    unit: str                    # canonical unit
    valid_range: Optional[Tuple[float, float]]
    aggregation: str             # mean, sum, last
    higher_is_better: Optional[bool]
    typical_frequency: str       # continuous, daily, ad_hoc


CANONICAL_METRICS: Dict[str, CanonicalMetric] = {

    # ── Wearables: Sleep ───────────────────────
    "sleep_duration": CanonicalMetric(
        key="sleep_duration",
        domain="sleep",
        unit="minutes",
        valid_range=(120, 720),
        aggregation="sum",
        higher_is_better=True,
        typical_frequency="daily",
    ),

    # ── Wearables: Recovery ────────────────────
    "hrv_rmssd": CanonicalMetric(
        key="hrv_rmssd",
        domain="recovery",
        unit="ms",
        valid_range=(5, 200),
        aggregation="mean",
        higher_is_better=True,
        typical_frequency="daily",
    ),

    "resting_hr": CanonicalMetric(
        key="resting_hr",
        domain="recovery",
        unit="bpm",
        valid_range=(30, 120),
        aggregation="mean",
        higher_is_better=False,
        typical_frequency="daily",
    ),

    # ── Labs ───────────────────────────────────
    "magnesium_serum": CanonicalMetric(
        key="magnesium_serum",
        domain="metabolic",
        unit="mmol/L",
        valid_range=(0.4, 1.2),
        aggregation="last",
        higher_is_better=True,
        typical_frequency="ad_hoc",
    ),

    "vitamin_d_25oh": CanonicalMetric(
        key="vitamin_d_25oh",
        domain="metabolic",
        unit="ng/ml",
        valid_range=(5, 150),
        aggregation="last",
        higher_is_better=True,
        typical_frequency="ad_hoc",
    ),

    # ── Subjective ─────────────────────────────
    "sleep_quality": CanonicalMetric(
        key="sleep_quality",
        domain="sleep",
        unit="score_0_10",
        valid_range=(0, 10),
        aggregation="mean",
        higher_is_better=True,
        typical_frequency="daily",
    ),

}
