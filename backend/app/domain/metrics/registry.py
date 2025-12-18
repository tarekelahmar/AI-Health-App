from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List


@dataclass(frozen=True)
class MetricSpec:
    """
    Canonical specification for a metric.

    Phase 1.1 notes:
    - This replaces older definitions in `core.metrics` and `domain.metric_registry`.
    - We keep `valid_range` as the single source of truth for numeric bounds.
    - `min_value`/`max_value` remain available as read-only properties for
      backward compatibility with existing ingestion / quality code.
    """

    key: str                        # "sleep_duration"
    domain: str                     # "sleep"
    display_name: str               # "Sleep Duration"
    unit: str                       # canonical unit, e.g. "minutes"
    valid_range: Tuple[float, float]
    direction: str                  # "higher_better" | "lower_better" | "optimal_range"
    optimal_range: Optional[Tuple[float, float]]
    aggregation: str                # "mean" | "sum"
    expected_cadence: str           # "daily" | "hourly" | "continuous"
    population_reference: Optional[Dict]

    # --- Backwards-compat properties (Phase 1.1 migration) -----------------
    @property
    def min_value(self) -> float:
        """
        Legacy alias used by existing ingestion / data quality code.
        Maps to the lower bound of `valid_range`.
        """
        return self.valid_range[0]

    @property
    def max_value(self) -> float:
        """
        Legacy alias used by existing ingestion / data quality code.
        Maps to the upper bound of `valid_range`.
        """
        return self.valid_range[1]


METRIC_REGISTRY: Dict[str, MetricSpec] = {
    # Wearables (objective)
    "sleep_duration": MetricSpec(
        key="sleep_duration",
        domain="sleep",
        display_name="Sleep Duration",
        unit="minutes",              # Keep minutes to avoid breaking existing ingestion/tests
        valid_range=(0, 1000),       # Matches legacy min/max in domain.metric_registry
        direction="higher_better",
        optimal_range=None,          # Can be refined later (e.g. 7–9 h equivalent)
        aggregation="sum",
        expected_cadence="daily",
        population_reference=None,
    ),
    "sleep_efficiency": MetricSpec(
        key="sleep_efficiency",
        domain="sleep",
        display_name="Sleep Efficiency",
        unit="percent",
        valid_range=(0, 100),
        direction="higher_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    "resting_hr": MetricSpec(
        key="resting_hr",
        domain="cardiometabolic",
        display_name="Resting Heart Rate",
        unit="bpm",
        valid_range=(20, 200),
        direction="lower_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    "hrv_rmssd": MetricSpec(
        key="hrv_rmssd",
        domain="stress",
        display_name="Heart Rate Variability (RMSSD)",
        unit="ms",
        valid_range=(0, 300),
        direction="higher_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    "steps": MetricSpec(
        key="steps",
        domain="activity",
        display_name="Steps",
        unit="count",
        valid_range=(0, 100000),
        direction="higher_better",
        optimal_range=None,
        aggregation="sum",
        expected_cadence="daily",
        population_reference=None,
    ),
    # Subjective metrics (self-report)
    "sleep_quality": MetricSpec(
        key="sleep_quality",
        domain="sleep",
        display_name="Sleep Quality (1–5)",
        unit="score_1_5",
        valid_range=(1, 5),
        direction="higher_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    "energy": MetricSpec(
        key="energy",
        domain="energy_fatigue",
        display_name="Energy (1–5)",
        unit="score_1_5",
        valid_range=(1, 5),
        direction="higher_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    "stress": MetricSpec(
        key="stress",
        domain="stress_nervous_system",
        display_name="Stress (1–5)",
        unit="score_1_5",
        valid_range=(1, 5),
        direction="lower_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    # Optional future-friendly aliases (not yet widely used, kept for completeness)
    "hrv": MetricSpec(
        key="hrv",
        domain="stress_nervous_system",
        display_name="Heart Rate Variability",
        unit="ms",
        valid_range=(5, 300),
        direction="higher_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
    "resting_heart_rate": MetricSpec(
        key="resting_heart_rate",
        domain="cardiometabolic",
        display_name="Resting Heart Rate",
        unit="bpm",
        valid_range=(30, 200),
        direction="lower_better",
        optimal_range=None,
        aggregation="mean",
        expected_cadence="daily",
        population_reference=None,
    ),
}


def get_metric_spec(metric: str) -> MetricSpec:
    if metric not in METRIC_REGISTRY:
        raise KeyError(f"Metric not registered: {metric}")
    return METRIC_REGISTRY[metric]


def list_metrics() -> List[str]:
    return list(METRIC_REGISTRY.keys())


