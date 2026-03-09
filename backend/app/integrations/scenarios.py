"""
Pre-defined health scenarios for testing specific system behaviors.

These are used by the synthetic data factory / demo provider to shape
daily patterns (sleep debt, illness episodes, extended stress, etc.).
"""

from __future__ import annotations

from typing import Dict

# Scenario schedules: {day_offset: scenario_name}
SCENARIOS: Dict[str, Dict[int, str]] = {
    "healthy_baseline": {
        # 30 days of normal variation – no explicit overrides.
    },
    "sleep_debt_accumulation": {
        # Days 7-14: progressively worsening sleep (mapped to factory-level scenario tags).
        7: "mild_sleep_debt",
        8: "mild_sleep_debt",
        9: "mild_sleep_debt",
        10: "moderate_sleep_debt",
        11: "moderate_sleep_debt",
        12: "severe_sleep_debt",
        13: "severe_sleep_debt",
        14: "severe_sleep_debt",
        # Days 15-17: recovery
        15: "recovery",
        16: "recovery",
        17: "recovery",
    },
    "illness_episode": {
        # Days 10-13: illness
        10: "illness",
        11: "illness",
        12: "illness",
        13: "illness",
        # Days 14-17: recovery
        14: "recovery",
        15: "recovery",
        16: "recovery",
        17: "recovery",
    },
    "stress_period": {
        # Days 7-21: elevated stress
        **{d: "stress" for d in range(7, 22)},
    },
    "intervention_response": {
        # Baseline days 0-13
        # Intervention starts day 14, positive response
        14: "slight_improvement",
        15: "slight_improvement",
        16: "moderate_improvement",
        17: "moderate_improvement",
        18: "moderate_improvement",
        19: "good_improvement",
        20: "good_improvement",
    },
}


def get_scenario_description(name: str) -> str:
    """Return human-readable description of scenario."""
    descriptions = {
        "healthy_baseline": "30 days of normal health variation, no significant events",
        "sleep_debt_accumulation": "Progressive sleep debt followed by recovery",
        "illness_episode": "Acute illness with recovery period",
        "stress_period": "Extended high-stress period affecting HRV and sleep",
        "intervention_response": "Baseline followed by positive intervention response",
    }
    return descriptions.get(name, "Unknown scenario")


