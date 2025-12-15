from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class DriverSpec:
    """Specification for a driver that can affect outcomes"""
    driver_key: str
    driver_type: str  # "behavior" | "supplement" | "intervention" | "lab_marker"
    outcome_metrics: List[str]  # Which metrics this driver can affect
    expected_direction: Optional[str]  # "positive" | "negative" | None (unknown)
    max_lag_days: int  # Maximum lag window to test
    min_data_days: int  # Minimum data required for attribution


# Driver Registry: defines which drivers can affect which outcomes
DRIVER_REGISTRY: Dict[str, DriverSpec] = {
    # Behaviors
    "alcohol_evening": DriverSpec(
        driver_key="alcohol_evening",
        driver_type="behavior",
        outcome_metrics=["sleep_duration", "sleep_efficiency", "sleep_quality", "hrv_rmssd"],
        expected_direction="negative",
        max_lag_days=2,
        min_data_days=10,
    ),
    "caffeine_pm": DriverSpec(
        driver_key="caffeine_pm",
        driver_type="behavior",
        outcome_metrics=["sleep_duration", "sleep_efficiency", "sleep_quality"],
        expected_direction="negative",
        max_lag_days=1,
        min_data_days=10,
    ),
    "exercise": DriverSpec(
        driver_key="exercise",
        driver_type="behavior",
        outcome_metrics=["sleep_duration", "sleep_quality", "hrv_rmssd", "resting_hr", "energy"],
        expected_direction="positive",
        max_lag_days=2,
        min_data_days=10,
    ),
    
    # Supplements (from behaviors_json or interventions)
    "melatonin": DriverSpec(
        driver_key="melatonin",
        driver_type="supplement",
        outcome_metrics=["sleep_duration", "sleep_efficiency", "sleep_quality"],
        expected_direction="positive",
        max_lag_days=2,
        min_data_days=7,
    ),
    "magnesium": DriverSpec(
        driver_key="magnesium",
        driver_type="supplement",
        outcome_metrics=["sleep_duration", "sleep_quality", "hrv_rmssd", "energy", "stress"],
        expected_direction="positive",
        max_lag_days=3,
        min_data_days=10,
    ),
    "omega3": DriverSpec(
        driver_key="omega3",
        driver_type="supplement",
        outcome_metrics=["hrv_rmssd", "resting_hr", "energy", "mood"],
        expected_direction="positive",
        max_lag_days=7,
        min_data_days=14,
    ),
    
    # Interventions (from experiments)
    "magnesium_glycinate": DriverSpec(
        driver_key="magnesium_glycinate",
        driver_type="intervention",
        outcome_metrics=["sleep_duration", "sleep_quality", "hrv_rmssd", "energy"],
        expected_direction="positive",
        max_lag_days=3,
        min_data_days=10,
    ),
    
    # Lab markers (carried forward)
    "vitamin_d": DriverSpec(
        driver_key="vitamin_d",
        driver_type="lab_marker",
        outcome_metrics=["energy", "mood", "hrv_rmssd"],
        expected_direction="positive",
        max_lag_days=30,  # Labs change slowly
        min_data_days=1,  # Just need one lab value
    ),
}


def get_driver_spec(driver_key: str) -> Optional[DriverSpec]:
    """Get driver specification by key"""
    return DRIVER_REGISTRY.get(driver_key)


def get_drivers_for_outcome(outcome_metric: str) -> List[DriverSpec]:
    """Get all drivers that can affect a given outcome metric"""
    return [
        spec for spec in DRIVER_REGISTRY.values()
        if outcome_metric in spec.outcome_metrics
    ]


def get_all_driver_keys() -> List[str]:
    """Get all registered driver keys"""
    return list(DRIVER_REGISTRY.keys())

