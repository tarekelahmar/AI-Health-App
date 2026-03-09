"""
Synthetic health data generator.

Generates statistically realistic health metrics with:
- Personal baselines (vary per "user")
- Day-to-day natural variation
- Weekly/seasonal patterns
- Correlated metrics (poor sleep → lower HRV)

Phase 1 scope:
- Daily cadence only (per-day aggregates), aligned with current loop runner.
- Metrics focus on sleep + recovery signals; additional signals are optional
  and may not yet participate in all detectors.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np


@dataclass
class PersonalProfile:
    """Defines a synthetic user's baseline health characteristics."""

    # Sleep (hours)
    sleep_duration_baseline: float = 7.2  # hours
    sleep_efficiency_baseline: float = 0.85

    # HRV / Resting HR
    hrv_baseline: float = 45.0  # ms
    rhr_baseline: float = 58.0  # bpm

    # Variability (how much day-to-day noise)
    noise_level: float = 0.15  # 15% variation

    # Correlations
    sleep_hrv_correlation: float = 0.6


class HealthDataFactory:
    """Generates synthetic health data for testing."""

    def __init__(self, profile: Optional[PersonalProfile] = None, seed: int = 42):
        self.profile = profile or PersonalProfile()
        self.rng = np.random.default_rng(seed)

    def generate_day(
        self,
        date: datetime,
        scenario: Optional[str] = None,
    ) -> Dict[str, float]:
        """Generate one day of health metrics."""

        # Base values with natural variation
        noise = self.rng.normal(0, self.profile.noise_level)

        # Weekly pattern (weekends slightly different)
        weekend_effect = 0.05 if date.weekday() >= 5 else 0.0

        sleep_duration = self.profile.sleep_duration_baseline * (1 + noise + weekend_effect)
        sleep_efficiency = min(0.98, self.profile.sleep_efficiency_baseline * (1 + noise * 0.5))

        # HRV correlates with sleep quality
        sleep_quality_factor = (sleep_duration / 7.5) * sleep_efficiency
        hrv = self.profile.hrv_baseline * (
            1
            + noise * 0.3
            + (sleep_quality_factor - 1) * self.profile.sleep_hrv_correlation
        )

        rhr = self.profile.rhr_baseline * (1 - noise * 0.2)  # Inverse relationship

        # Apply scenario modifiers (Phase 1: coarse-grained only).
        if scenario == "illness":
            hrv *= 0.7
            rhr *= 1.15
            sleep_efficiency *= 0.85
        elif scenario == "stress":
            hrv *= 0.85
            sleep_duration *= 0.9
            sleep_efficiency *= 0.92
        elif scenario == "recovery":
            hrv *= 1.1
            sleep_duration *= 1.1

        # Clamp some values into plausible ranges; we intentionally keep
        # randomness a bit messy to avoid over-optimistic detectors.
        hrv = max(15.0, hrv)
        rhr = max(45.0, rhr)

        return {
            # NOTE: sleep_duration here is in hours; callers (e.g. DemoProvider)
            # are responsible for mapping to canonical units if needed.
            "sleep_duration": round(sleep_duration, 2),
            "sleep_efficiency": round(sleep_efficiency, 3),
            "hrv_rmssd": round(hrv, 1),
            # Use canonical short key for resting heart rate to match registry.
            "resting_hr": round(rhr, 0),
            # Additional signals (not all are in METRIC_REGISTRY yet)
            "respiratory_rate": round(14 + self.rng.normal(0, 1), 1),
            "skin_temp_deviation": round(self.rng.normal(0, 0.3), 2),
            "spo2": round(min(100, 96 + self.rng.normal(0, 1)), 1),
        }

    def generate_range(
        self,
        start_date: datetime,
        days: int,
        scenario_schedule: Optional[Dict[int, str]] = None,
    ) -> List[Dict]:
        """
        Generate multiple days of data.

        Args:
            start_date: first day
            days: number of days to generate (daily cadence)
            scenario_schedule: {day_offset: scenario_name} for specific patterns,
                e.g., {14: "illness", 15: "illness", 16: "illness", 17: "recovery"}.
        """
        scenario_schedule = scenario_schedule or {}
        results: List[Dict] = []

        for day_offset in range(days):
            date = start_date + timedelta(days=day_offset)
            scenario = scenario_schedule.get(day_offset)

            day_data = self.generate_day(date, scenario)
            day_data["date"] = date.isoformat()
            results.append(day_data)

        return results


