"""
Canonical health domain map (domain modeling only).

Purpose
-------
This module defines a conservative, non-diagnostic semantic layer that the system can
reference consistently across engines (loop runner, insights, narratives, suppression,
trust, etc.) without embedding analytics, causal logic, or recommendations.

Non-goals (intentional)
-----------------------
- No rules, thresholds, heuristics, confidence logic, or grading
- No causal claims or diagnostic language
- No prescriptive intervention/protocol content (only abstract categories)
- No UI, API, storage, or provider-specific implementation details

Design notes
------------
- Signals, symptoms, and labs are represented as *simple string identifiers*.
- Intervention types are abstract categories only (Enum).
- Domains can overlap; this registry does not deduplicate aggressively.
- This file is intended to be long-lived infrastructure; changes should be additive
  and carefully reviewed for semantic drift.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, Tuple


class InterventionType(str, Enum):
    """
    Abstract intervention category.

    These are *not* specific protocols or recommendations—just broad buckets that
    other parts of the system may use for labeling, grouping, or filtering.
    """

    BEHAVIORAL = "behavioral"
    ENVIRONMENTAL = "environmental"
    NUTRITIONAL = "nutritional"
    SUPPLEMENT = "supplement"
    DIAGNOSTIC = "diagnostic"
    MIND_BODY = "mind_body"
    LIFESTYLE = "lifestyle"
    EXERCISE = "exercise"
    DIETARY = "dietary"
    COGNITIVE = "cognitive"
    RECOVERY = "recovery"


class HealthDomainKey(str, Enum):
    """
    Stable identifiers for canonical health domains.

    Keys are snake_case and intended to be safe for persistence and cross-service use.
    """

    SLEEP = "sleep"
    STRESS_NERVOUS_SYSTEM = "stress_nervous_system"
    ENERGY_FATIGUE = "energy_fatigue"
    CARDIOMETABOLIC = "cardiometabolic"
    GASTROINTESTINAL = "gastrointestinal"
    INFLAMMATION_IMMUNE = "inflammation_immune"
    HORMONAL_REPRODUCTIVE = "hormonal_reproductive"
    COGNITIVE_MENTAL_PERFORMANCE = "cognitive_mental_performance"
    MUSCULOSKELETAL_RECOVERY = "musculoskeletal_recovery"
    NUTRITION_MICRONUTRIENTS = "nutrition_micronutrients"


@dataclass(frozen=True)
class HealthDomain:
    """
    Canonical mapping for a health domain.

    All identifiers are strings; no semantics beyond membership are implied.
    """

    key: HealthDomainKey
    display_name: str
    # Short neutral description for interpretability (non-diagnostic, non-actionable).
    description: str

    # String identifiers (canonical, not exhaustive)
    signals: Tuple[str, ...]
    symptoms: Tuple[str, ...]
    labs: Tuple[str, ...]

    # Abstract categories only (no specific interventions / protocols)
    intervention_types: Tuple[InterventionType, ...]


# Canonical registry (EXACTLY the domains requested; content is canonical, not exhaustive)
HEALTH_DOMAINS: Dict[HealthDomainKey, HealthDomain] = {
    HealthDomainKey.SLEEP: HealthDomain(
        key=HealthDomainKey.SLEEP,
        display_name="Sleep",
        description=(
            "Sleep-related insights are based on sleep timing/quality signals and overnight recovery metrics."
        ),
        signals=(
            "sleep_duration",
            "sleep_efficiency",
            "sleep_latency",
            "wake_after_sleep_onset",
            "hrv_overnight",
            "resting_hr_overnight",
        ),
        symptoms=(
            "insomnia",
            "non_restorative_sleep",
            "early_waking",
            "night_awakenings",
            "daytime_sleepiness",
        ),
        labs=(
            "cortisol_am",
            "ferritin",
            "magnesium",
            "vitamin_d",
            "tsh",
            "free_t3",
        ),
        intervention_types=(
            InterventionType.BEHAVIORAL,
            InterventionType.ENVIRONMENTAL,
            InterventionType.NUTRITIONAL,
            InterventionType.SUPPLEMENT,
            InterventionType.DIAGNOSTIC,
        ),
    ),
    HealthDomainKey.STRESS_NERVOUS_SYSTEM: HealthDomain(
        key=HealthDomainKey.STRESS_NERVOUS_SYSTEM,
        display_name="Stress & Nervous System",
        description=(
            "Stress & nervous system insights reflect patterns in autonomic and breathing-related signals."
        ),
        signals=(
            "hrv_day",
            "hrv_night",
            "resting_hr",
            "breathing_rate",
            "sleep_fragmentation",
        ),
        symptoms=(
            "anxiety",
            "irritability",
            "wired_but_tired",
            "panic",
            "poor_stress_tolerance",
        ),
        labs=(
            "cortisol_diurnal",
            "dhea_s",
            "crp",
        ),
        intervention_types=(
            InterventionType.BEHAVIORAL,
            InterventionType.MIND_BODY,
            InterventionType.LIFESTYLE,
            InterventionType.SUPPLEMENT,
            InterventionType.ENVIRONMENTAL,
        ),
    ),
    HealthDomainKey.ENERGY_FATIGUE: HealthDomain(
        key=HealthDomainKey.ENERGY_FATIGUE,
        display_name="Energy & Fatigue",
        description=(
            "Energy & fatigue insights summarize patterns in energy-related self-tracking and related trends."
        ),
        signals=(
            "subjective_energy",
            "activity_tolerance",
            "hrv_trend",
            "resting_hr_trend",
        ),
        symptoms=(
            "fatigue",
            "post_exertional_malaise",
            "brain_fog",
            "low_motivation",
        ),
        labs=(
            "ferritin",
            "vitamin_b12",
            "folate",
            "thyroid_panel",
            "cmp",
            "vitamin_d",
        ),
        intervention_types=(
            InterventionType.NUTRITIONAL,
            InterventionType.LIFESTYLE,
            InterventionType.SUPPLEMENT,
            InterventionType.DIAGNOSTIC,
        ),
    ),
    HealthDomainKey.CARDIOMETABOLIC: HealthDomain(
        key=HealthDomainKey.CARDIOMETABOLIC,
        display_name="Cardiometabolic",
        description=(
            "Cardiometabolic insights reference cardiovascular and activity-related signals and common labs."
        ),
        signals=(
            "resting_hr",
            "activity_level",
            "vo2_proxy",
            "weight",
        ),
        symptoms=(
            "exercise_intolerance",
            "shortness_of_breath",
            "palpitations",
        ),
        labs=(
            "hba1c",
            "fasting_glucose",
            "fasting_insulin",
            "lipid_panel",
            "hs_crp",
        ),
        intervention_types=(
            InterventionType.LIFESTYLE,
            InterventionType.NUTRITIONAL,
            InterventionType.EXERCISE,
            InterventionType.DIAGNOSTIC,
        ),
    ),
    HealthDomainKey.GASTROINTESTINAL: HealthDomain(
        key=HealthDomainKey.GASTROINTESTINAL,
        display_name="Gastrointestinal",
        description=(
            "Gastrointestinal insights are based on gut-related tracking signals, symptoms, and relevant labs."
        ),
        signals=(
            "stool_frequency",
            "gi_symptom_score",
            "hrv_meal_response",
        ),
        symptoms=(
            "bloating",
            "diarrhea",
            "constipation",
            "abdominal_pain",
            "reflux",
        ),
        labs=(
            "stool_test",
            "calprotectin",
            "zonulin",
            "celiac_markers",
        ),
        intervention_types=(
            InterventionType.DIETARY,
            InterventionType.SUPPLEMENT,
            InterventionType.LIFESTYLE,
            InterventionType.DIAGNOSTIC,
        ),
    ),
    HealthDomainKey.INFLAMMATION_IMMUNE: HealthDomain(
        key=HealthDomainKey.INFLAMMATION_IMMUNE,
        display_name="Inflammation & Immune",
        description=(
            "Inflammation & immune insights summarize patterns in recovery disruption signals and immune-related labs."
        ),
        signals=(
            "hrv_suppression",
            "resting_hr_elevation",
            "sleep_disruption",
        ),
        symptoms=(
            "joint_pain",
            "frequent_illness",
            "chronic_aches",
            "allergic_symptoms",
        ),
        labs=(
            "crp",
            "hs_crp",
            "esr",
            "ana",
            "cytokines",
        ),
        intervention_types=(
            InterventionType.NUTRITIONAL,
            InterventionType.LIFESTYLE,
            InterventionType.SUPPLEMENT,
            InterventionType.DIAGNOSTIC,
        ),
    ),
    HealthDomainKey.HORMONAL_REPRODUCTIVE: HealthDomain(
        key=HealthDomainKey.HORMONAL_REPRODUCTIVE,
        display_name="Hormonal & Reproductive",
        description=(
            "Hormonal & reproductive insights reference cycle-related tracking and commonly used hormone labs."
        ),
        signals=(
            "cycle_tracking",
            "sleep_variability",
            "body_temperature",
        ),
        symptoms=(
            "pms",
            "irregular_cycles",
            "libido_changes",
            "mood_changes",
        ),
        labs=(
            "estradiol",
            "progesterone",
            "testosterone",
            "lh",
            "fsh",
            "shbg",
            "prolactin",
        ),
        intervention_types=(
            InterventionType.LIFESTYLE,
            InterventionType.NUTRITIONAL,
            InterventionType.SUPPLEMENT,
            InterventionType.DIAGNOSTIC,
        ),
    ),
    HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE: HealthDomain(
        key=HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE,
        display_name="Cognitive & Mental Performance",
        description=(
            "Cognitive & mental performance insights summarize attention/processing signals and related contributors."
        ),
        signals=(
            "reaction_time",
            "focus_score",
            "sleep_quality",
            "hrv",
        ),
        symptoms=(
            "brain_fog",
            "poor_focus",
            "memory_issues",
        ),
        labs=(
            "vitamin_b12",
            "folate",
            "iron_studies",
            "thyroid_panel",
        ),
        intervention_types=(
            InterventionType.LIFESTYLE,
            InterventionType.COGNITIVE,
            InterventionType.NUTRITIONAL,
            InterventionType.SUPPLEMENT,
        ),
    ),
    HealthDomainKey.MUSCULOSKELETAL_RECOVERY: HealthDomain(
        key=HealthDomainKey.MUSCULOSKELETAL_RECOVERY,
        display_name="Musculoskeletal & Recovery",
        description=(
            "Musculoskeletal & recovery insights reference training load, soreness, and recovery-related signals."
        ),
        signals=(
            "training_load",
            "hrv_recovery",
            "resting_hr",
            "subjective_soreness",
        ),
        symptoms=(
            "muscle_soreness",
            "joint_pain",
            "slow_recovery",
        ),
        labs=(
            "ck",
            "vitamin_d",
            "magnesium",
        ),
        intervention_types=(
            InterventionType.EXERCISE,
            InterventionType.RECOVERY,
            InterventionType.LIFESTYLE,
            InterventionType.SUPPLEMENT,
        ),
    ),
    HealthDomainKey.NUTRITION_MICRONUTRIENTS: HealthDomain(
        key=HealthDomainKey.NUTRITION_MICRONUTRIENTS,
        display_name="Nutrition & Micronutrients",
        description=(
            "Nutrition & micronutrient insights reference dietary tracking, body-weight trends, and common nutrient labs."
        ),
        signals=(
            "dietary_logs",
            "weight_trend",
            "energy_level",
        ),
        symptoms=(
            "cravings",
            "poor_satiety",
            "gi_symptoms",
        ),
        labs=(
            "vitamin_d",
            "vitamin_b12",
            "folate",
            "iron",
            "zinc",
            "magnesium",
        ),
        intervention_types=(
            InterventionType.DIETARY,
            InterventionType.SUPPLEMENT,
            InterventionType.LIFESTYLE,
        ),
    ),
}


def domain_for_signal(signal_id: str) -> Optional[HealthDomainKey]:
    """
    Deterministically map a primary signal/metric identifier to a single domain key.

    IMPORTANT:
    - This is *membership-based only* (no heuristics, no inference).
    - Overlap is allowed in the registry; when a signal appears in multiple domains,
      we return the first match in HEALTH_DOMAINS insertion order for determinism.
    - Unknown signals return None (callers should handle safely).
    """
    if not signal_id:
        return None
    for dk, domain in HEALTH_DOMAINS.items():
        if signal_id in domain.signals:
            return dk
    return None



