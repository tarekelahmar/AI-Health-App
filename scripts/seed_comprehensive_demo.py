"""
Comprehensive seed script for the AI Health Platform.

Generates 90 days of realistic, correlated demo data across ALL domain models,
creating an embedded health "story" that exercises every frontend page.

The Story (90 days):
  Days  1-30: Baseline      - Normal tracking, system learns baselines
  Days 31-45: Stress        - Work deadline, sleep degrades, HRV drops
  Days 46-75: Experiment    - Magnesium glycinate 400mg, gradual improvement
  Days 76-90: Stabilization - Full recovery, causal patterns learned

Usage:
    cd backend && PYTHONPATH=. python ../scripts/seed_comprehensive_demo.py
    # OR from project root:
    make seed-demo
"""

import sys
import json
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

import numpy as np
from datetime import datetime, date, timedelta
from collections import defaultdict

from sqlalchemy import text

from app.core.database import SessionLocal, Base, engine
from app.integrations.data_factory import HealthDataFactory, PersonalProfile
from app.domain.models import (
    User, Consent, ProviderToken, DataProvenance,
    HealthDataPoint, WearableSample, DailyCheckIn, Symptom, LabResult,
    Baseline, WellnessScore, TrustScore, PersonalHealthModel,
    Intervention, Protocol, Experiment, AdherenceEvent, EvaluationResult,
    Insight, Narrative, InsightSummary,
    DriverFinding, PersonalDriver, PersonalPattern, CausalMemory,
    CausalGraphEdge, CausalGraphSnapshot, ExplanationEdge,
    InboxItem, NotificationOutbox, AuditEvent, DecisionSignal,
)

# ─── Constants ──────────────────────────────────────────────
DEMO_USER_ID = 1
DEMO_EMAIL = "demo@example.com"
TOTAL_DAYS = 90
SEED = 42

# Story phase boundaries (day offsets, 0-indexed)
BASELINE_END = 30
STRESS_START = 30
STRESS_END = 45
EXPERIMENT_START = 45
EXPERIMENT_END = 75
STABILIZATION_START = 75

# Metric key aliases: Set A -> (Set B key, transform function)
METRIC_ALIASES = {
    "sleep_duration": ("sleep_duration_minutes", lambda v: v * 60),   # hours -> minutes
    "sleep_efficiency": ("sleep_efficiency_pct", lambda v: v * 100),  # ratio -> percent
    "hrv_rmssd": ("hrv_rmssd_ms", lambda v: v),                      # already ms
    "resting_hr": ("resting_heart_rate_bpm", lambda v: v),            # already bpm
}

SUBJECTIVE_ALIASES = {
    "energy": "subjective_energy",
    "stress": "subjective_stress",
}


# ─── Helpers ────────────────────────────────────────────────

def get_phase(day_offset: int) -> str:
    """Return the story phase for a given day offset."""
    if day_offset < BASELINE_END:
        return "baseline"
    elif day_offset < STRESS_END:
        return "stress"
    elif day_offset < EXPERIMENT_END:
        return "experiment"
    else:
        return "stabilization"


def build_scenario_schedule() -> dict:
    """Build scenario schedule for HealthDataFactory."""
    schedule = {}
    for d in range(STRESS_START, STRESS_END):
        schedule[d] = "stress"
    # Early experiment days still stressed
    for d in range(EXPERIMENT_START, EXPERIMENT_START + 7):
        schedule[d] = "stress"
    # Remaining experiment and stabilization = recovery
    for d in range(EXPERIMENT_START + 7, TOTAL_DAYS):
        schedule[d] = "recovery"
    return schedule


def generate_subjective_scores(phase: str, day_offset: int, rng) -> dict:
    """Generate phase-aware subjective scores (1-5 scale) for HealthDataPoint."""
    # Base values per phase
    bases = {
        "baseline":      {"energy": 3.5, "stress": 2.5, "mood": 3.5, "focus": 3.5, "sleep_quality": 3.5},
        "stress":        {"energy": 2.2, "stress": 4.2, "mood": 2.5, "focus": 2.3, "sleep_quality": 2.3},
        "experiment":    {"energy": 3.0, "stress": 3.0, "mood": 3.0, "focus": 3.0, "sleep_quality": 3.0},
        "stabilization": {"energy": 4.0, "stress": 2.0, "mood": 4.0, "focus": 4.0, "sleep_quality": 4.0},
    }
    base = bases.get(phase, bases["baseline"])

    # Gradual improvement during experiment phase
    if phase == "experiment":
        progress = (day_offset - EXPERIMENT_START) / (EXPERIMENT_END - EXPERIMENT_START)
        for k in base:
            if k == "stress":
                base[k] = 3.5 - progress * 1.2  # stress decreases
            else:
                base[k] = 2.8 + progress * 1.5  # others improve

    scores = {}
    for k, v in base.items():
        noisy = v + rng.normal(0, 0.3)
        scores[k] = max(1.0, min(5.0, round(noisy, 1)))
    return scores


def generate_checkin_scores(phase: str, day_offset: int, rng) -> dict:
    """Generate phase-aware subjective scores (0-10 scale) for DailyCheckIn."""
    # Base values per phase (0-10 scale)
    bases = {
        "baseline":      {"sleep_quality": 7, "energy": 7, "mood": 7, "stress": 3, "focus": 7},
        "stress":        {"sleep_quality": 4, "energy": 4, "mood": 4, "stress": 8, "focus": 4},
        "experiment":    {"sleep_quality": 5, "energy": 5, "mood": 5, "stress": 5, "focus": 5},
        "stabilization": {"sleep_quality": 8, "energy": 8, "mood": 8, "stress": 2, "focus": 8},
    }
    base = bases.get(phase, bases["baseline"])

    if phase == "experiment":
        progress = (day_offset - EXPERIMENT_START) / (EXPERIMENT_END - EXPERIMENT_START)
        base = {
            "sleep_quality": int(4 + progress * 5),
            "energy": int(4 + progress * 5),
            "mood": int(4 + progress * 4),
            "stress": int(7 - progress * 5),
            "focus": int(4 + progress * 4),
        }

    scores = {}
    for k, v in base.items():
        noisy = v + rng.normal(0, 1)
        scores[k] = max(0, min(10, int(round(noisy))))
    return scores


# ─── Clear ──────────────────────────────────────────────────

def clear_demo_data(db) -> None:
    """Delete all data for demo user. Reverse FK order.

    Uses raw connection to handle missing tables gracefully on PostgreSQL
    (where a failed statement aborts the transaction).
    """
    print("  Clearing existing demo data...")
    tables = [
        "decision_signals", "audit_events", "notification_outbox",
        "explanation_edges", "causal_graph_snapshots", "causal_graph_edges",
        "causal_memory", "personal_patterns", "personal_drivers", "driver_findings",
        "insight_summaries", "narratives", "insights",
        "evaluation_results", "adherence_events", "experiments",
        "protocols", "interventions",
        "wellness_scores", "trust_scores", "personal_health_models",
        "baselines", "symptoms", "daily_checkins", "lab_results",
        "wearable_samples", "health_data", "data_provenance",
        "inbox_items", "provider_tokens", "consents",
        "oauth_states", "loop_decisions", "questionnaires",
    ]
    # Use savepoints so a failed DELETE doesn't abort the whole transaction
    for table in tables:
        try:
            db.execute(text("SAVEPOINT sp_clear"))
            db.execute(text(f"DELETE FROM {table} WHERE user_id = :uid"), {"uid": DEMO_USER_ID})
            db.execute(text("RELEASE SAVEPOINT sp_clear"))
        except Exception:
            db.execute(text("ROLLBACK TO SAVEPOINT sp_clear"))
    # Delete user last
    try:
        db.execute(text("SAVEPOINT sp_clear"))
        db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": DEMO_USER_ID})
        db.execute(text("RELEASE SAVEPOINT sp_clear"))
    except Exception:
        db.execute(text("ROLLBACK TO SAVEPOINT sp_clear"))
    db.commit()
    print("  Done clearing.")


# ─── Tier 0: Foundation ─────────────────────────────────────

def seed_user(db) -> User:
    """Create demo user."""
    user = User(
        id=DEMO_USER_ID,
        name="Demo User",
        email=DEMO_EMAIL,
        hashed_password="not_relevant_for_demo",
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.flush()
    print(f"  User: {user.email} (id={user.id})")
    return user


def seed_consent(db, user_id: int) -> Consent:
    """Create full consent record."""
    consent = Consent(
        user_id=user_id,
        consent_version="1.0",
        consent_timestamp=datetime.utcnow(),
        understands_not_medical_advice=True,
        consents_to_data_analysis=True,
        understands_recommendations_experimental=True,
        understands_can_stop_anytime=True,
        consents_to_whoop_ingestion=True,
        consents_to_fitbit_ingestion=False,
        consents_to_oura_ingestion=False,
        onboarding_completed=True,
        onboarding_completed_at=datetime.utcnow(),
    )
    db.add(consent)
    return consent


def seed_provider_token(db, user_id: int) -> ProviderToken:
    """Create demo provider token so InsightsFeed doesn't show 'no provider' state."""
    token = ProviderToken(
        user_id=user_id,
        provider="whoop",
        access_token="demo_access_token_not_real",
        refresh_token="demo_refresh_token_not_real",
        token_type="bearer",
        scope="read:profile read:body read:sleep read:workout read:recovery",
        expires_at=datetime.utcnow() + timedelta(days=365),
    )
    db.add(token)
    return token


# ─── Tier 1: Raw Time Series ────────────────────────────────

def seed_health_data_points(db, user_id: int, start_date: datetime, factory, rng) -> list:
    """Generate 90 days of HealthDataPoint rows with both key sets."""
    print("  Seeding HealthDataPoints...")
    scenario_schedule = build_scenario_schedule()
    raw_data = factory.generate_range(
        start_date=start_date,
        days=TOTAL_DAYS,
        scenario_schedule=scenario_schedule,
    )

    all_points = []

    for day_offset, day_data in enumerate(raw_data):
        ts = start_date + timedelta(days=day_offset)
        phase = get_phase(day_offset)

        # 1. Wearable metrics from factory
        wearable_metrics = {
            "sleep_duration": (day_data["sleep_duration"], "hours"),
            "sleep_efficiency": (day_data["sleep_efficiency"], "ratio"),
            "hrv_rmssd": (day_data["hrv_rmssd"], "ms"),
            "resting_hr": (day_data["resting_hr"], "bpm"),
        }

        for key, (value, unit) in wearable_metrics.items():
            point = HealthDataPoint(
                user_id=user_id, metric_type=key,
                value=round(value, 2), unit=unit,
                timestamp=ts, source="wearable",
            )
            db.add(point)
            all_points.append(point)

            # Set B alias
            if key in METRIC_ALIASES:
                alias_key, transform = METRIC_ALIASES[key]
                alias_unit_map = {
                    "sleep_duration_minutes": "minutes",
                    "sleep_efficiency_pct": "percent",
                    "hrv_rmssd_ms": "ms",
                    "resting_heart_rate_bpm": "bpm",
                }
                ap = HealthDataPoint(
                    user_id=user_id, metric_type=alias_key,
                    value=round(transform(value), 2),
                    unit=alias_unit_map.get(alias_key, unit),
                    timestamp=ts, source="wearable",
                )
                db.add(ap)
                all_points.append(ap)

        # 2. Respiratory rate (+ alias)
        rr = day_data.get("respiratory_rate", 14.5)
        db.add(HealthDataPoint(
            user_id=user_id, metric_type="respiratory_rate",
            value=round(rr, 1), unit="brpm", timestamp=ts, source="wearable",
        ))
        db.add(HealthDataPoint(
            user_id=user_id, metric_type="respiratory_rate_brpm",
            value=round(rr, 1), unit="brpm", timestamp=ts, source="wearable",
        ))

        # 3. Steps
        step_bases = {"baseline": 8000, "stress": 5500, "experiment": 7000, "stabilization": 9000}
        steps = step_bases.get(phase, 8000) + rng.normal(0, 1500)
        db.add(HealthDataPoint(
            user_id=user_id, metric_type="steps",
            value=max(500, round(steps)), unit="count",
            timestamp=ts, source="wearable",
        ))

        # 4. Subjective metrics (1-5 scale)
        subjective = generate_subjective_scores(phase, day_offset, rng)
        for key, value in subjective.items():
            p = HealthDataPoint(
                user_id=user_id, metric_type=key,
                value=round(value, 1), unit="score_1_5",
                timestamp=ts, source="manual",
            )
            db.add(p)
            all_points.append(p)

            # Set B alias for subjective
            if key in SUBJECTIVE_ALIASES:
                ap = HealthDataPoint(
                    user_id=user_id, metric_type=SUBJECTIVE_ALIASES[key],
                    value=round(value, 1), unit="score_1_5",
                    timestamp=ts, source="manual",
                )
                db.add(ap)
                all_points.append(ap)

    print(f"    -> {len(all_points)} points (+ aliases)")
    return all_points


def seed_wearable_samples(db, user_id: int, start_date: datetime, health_data: list) -> None:
    """Populate legacy wearable_samples table."""
    print("  Seeding WearableSamples (legacy)...")
    count = 0
    # Group by date, pick core metrics
    by_date = defaultdict(dict)
    for p in health_data:
        if p.source == "wearable" and p.metric_type in ("sleep_duration", "hrv_rmssd", "resting_hr", "sleep_efficiency"):
            day_key = p.timestamp.date()
            by_date[day_key][p.metric_type] = p

    for day_key, metrics in by_date.items():
        for metric_type, p in metrics.items():
            ws = WearableSample(
                user_id=user_id,
                device_type="demo",
                metric_type=metric_type,
                value=p.value,
                unit=p.unit,
                timestamp=p.timestamp,
                device_id="demo_device_001",
            )
            db.add(ws)
            count += 1
    print(f"    -> {count} samples")


def seed_daily_checkins(db, user_id: int, start_date: date, rng) -> list:
    """Generate 90 days of DailyCheckIn records."""
    print("  Seeding DailyCheckIns...")
    checkins = []
    notes_map = {
        0: "First day of tracking! Feeling optimistic.",
        29: "One month in. Baselines should be set.",
        32: "Big project deadline coming up. Stressed.",
        38: "Not sleeping well. Work is intense.",
        45: "Starting magnesium glycinate experiment today. 400mg before bed.",
        52: "A week into magnesium. Maybe sleeping slightly better?",
        65: "Definitely noticing better sleep. Less waking up at night.",
        75: "Experiment complete! Sleep feels much better.",
        80: "Back to feeling great. Energy is solid.",
    }

    for day_offset in range(TOTAL_DAYS):
        d = start_date + timedelta(days=day_offset)
        phase = get_phase(day_offset)
        scores = generate_checkin_scores(phase, day_offset, rng)

        behaviors = {}
        if day_offset >= EXPERIMENT_START and day_offset < EXPERIMENT_END:
            # Experiment period - log magnesium
            took_it = rng.random() < 0.85  # 85% adherence
            behaviors = {
                "took_magnesium": took_it,
                "magnesium_mg": 400 if took_it else 0,
            }
        if phase == "stress":
            behaviors["caffeine_late"] = rng.random() < 0.4  # more late caffeine during stress

        checkin = DailyCheckIn(
            user_id=user_id,
            checkin_date=d,
            sleep_quality=scores["sleep_quality"],
            energy=scores["energy"],
            mood=scores["mood"],
            stress=scores["stress"],
            focus=scores["focus"],
            notes=notes_map.get(day_offset),
            behaviors_json=behaviors,
            adherence_rate=0.85 if day_offset >= EXPERIMENT_START and day_offset < EXPERIMENT_END else None,
        )
        db.add(checkin)
        checkins.append(checkin)

    print(f"    -> {len(checkins)} check-ins")
    return checkins


def seed_symptoms(db, user_id: int, start_date: datetime) -> None:
    """Create symptoms during stress period."""
    print("  Seeding Symptoms...")
    count = 0
    for day_offset in range(STRESS_START, STRESS_END + 10):  # fatigue lingers into experiment
        ts = start_date + timedelta(days=day_offset)
        severity = "severe" if day_offset < STRESS_END else "moderate"
        db.add(Symptom(
            user_id=user_id, symptom_name="fatigue",
            severity=severity, frequency="daily",
            notes="Low energy, need more coffee.",
            timestamp=ts,
        ))
        count += 1

    for day_offset in range(STRESS_START + 5, STRESS_END):
        ts = start_date + timedelta(days=day_offset)
        db.add(Symptom(
            user_id=user_id, symptom_name="brain_fog",
            severity="mild", frequency="occasional",
            notes="Hard to concentrate in the afternoon.",
            timestamp=ts,
        ))
        count += 1

    print(f"    -> {count} symptoms")


def seed_lab_results(db, user_id: int, start_date: datetime) -> None:
    """4 lab draws across 90 days."""
    print("  Seeding LabResults...")
    draws = [
        (0, {  # Day 1 - baseline
            "fasting_glucose":  (5.2, "mmol/L", "3.8-5.5"),
            "vitamin_d":        (72, "nmol/L", "50-125"),
            "hs_crp":           (0.8, "mg/L", "0-3.0"),
            "ferritin":         (85, "ng/mL", "30-300"),
            "magnesium":        (0.82, "mmol/L", "0.7-1.0"),
        }),
        (30, {  # Day 30 - post baseline
            "fasting_glucose":  (5.4, "mmol/L", "3.8-5.5"),
            "vitamin_d":        (68, "nmol/L", "50-125"),
            "hs_crp":           (1.4, "mg/L", "0-3.0"),  # stress elevates inflammation
            "ferritin":         (82, "ng/mL", "30-300"),
            "magnesium":        (0.80, "mmol/L", "0.7-1.0"),
        }),
        (60, {  # Day 60 - mid experiment
            "fasting_glucose":  (5.3, "mmol/L", "3.8-5.5"),
            "vitamin_d":        (70, "nmol/L", "50-125"),
            "hs_crp":           (1.1, "mg/L", "0-3.0"),
            "ferritin":         (80, "ng/mL", "30-300"),
            "magnesium":        (0.88, "mmol/L", "0.7-1.0"),  # supplementation effect
        }),
        (89, {  # Day 90 - post stabilization
            "fasting_glucose":  (5.1, "mmol/L", "3.8-5.5"),
            "vitamin_d":        (75, "nmol/L", "50-125"),
            "hs_crp":           (0.7, "mg/L", "0-3.0"),
            "ferritin":         (88, "ng/mL", "30-300"),
            "magnesium":        (0.92, "mmol/L", "0.7-1.0"),
        }),
    ]
    count = 0
    for day_offset, tests in draws:
        ts = start_date + timedelta(days=day_offset)
        for test_name, (value, unit, ref_range) in tests.items():
            db.add(LabResult(
                user_id=user_id, test_name=test_name,
                value=value, unit=unit,
                reference_range=ref_range,
                timestamp=ts, lab_name="DemoLab",
            ))
            count += 1
    print(f"    -> {count} lab results")


def seed_data_provenance(db, user_id: int) -> None:
    """Create provenance records."""
    for i, (stype, sname, run_id) in enumerate([
        ("wearable", "demo", "demo_ingest_001"),
        ("lab", "demolab", "demo_ingest_002"),
        ("manual", "user", "demo_ingest_003"),
    ]):
        db.add(DataProvenance(
            user_id=user_id,
            source_type=stype,
            source_name=sname,
            ingestion_run_id=run_id,
            received_at=datetime.utcnow(),
            is_validated=True,
        ))


# ─── Tier 2: Derived Analytics ──────────────────────────────

def seed_baselines(db, user_id: int, health_data: list) -> None:
    """Compute baselines from first 30 days of actual data."""
    print("  Seeding Baselines...")
    # Group by metric_type, filter to baseline period
    metric_values = defaultdict(list)
    cutoff = min(p.timestamp for p in health_data) + timedelta(days=30)
    for p in health_data:
        if p.timestamp <= cutoff and p.user_id == user_id:
            metric_values[p.metric_type].append(p.value)

    count = 0
    for metric_type, values in metric_values.items():
        if len(values) < 7:
            continue
        arr = np.array(values)
        median_val = float(np.median(arr))
        mad_val = float(np.median(np.abs(arr - median_val))) * 1.4826

        bl = Baseline(
            user_id=user_id,
            metric_type=metric_type,
            mean=round(median_val, 4),
            std=round(max(mad_val, 0.01), 4),  # avoid zero
            method="median_mad",
            n_samples=len(values),
            ci_80_low=round(float(np.percentile(arr, 10)), 4),
            ci_80_high=round(float(np.percentile(arr, 90)), 4),
            ci_95_low=round(float(np.percentile(arr, 2.5)), 4),
            ci_95_high=round(float(np.percentile(arr, 97.5)), 4),
            is_stable=len(values) >= 14,
            outliers_detected=0,
            window_days=30,
        )
        db.add(bl)
        count += 1
    print(f"    -> {count} baselines")


def seed_wellness_scores(db, user_id: int, start_date: date, checkins: list, health_data: list) -> None:
    """Generate 90 days of WellnessScore from actual check-in and wearable data."""
    print("  Seeding WellnessScores...")
    checkin_by_date = {c.checkin_date: c for c in checkins}

    # Index wearable data by date
    wearable_by_date = defaultdict(dict)
    for p in health_data:
        if p.source == "wearable":
            day = p.timestamp.date()
            wearable_by_date[day][p.metric_type] = p.value

    for day_offset in range(TOTAL_DAYS):
        score_date = start_date + timedelta(days=day_offset)
        checkin = checkin_by_date.get(score_date)
        wearable = wearable_by_date.get(score_date, {})

        # Objective score (0-100) from wearable data
        obj_components = []
        if "hrv_rmssd" in wearable:
            # HRV: higher is better, baseline ~45ms, scale 20-70 -> 0-100
            hrv_score = max(0, min(100, (wearable["hrv_rmssd"] - 20) / 50 * 100))
            obj_components.append(hrv_score)
        if "sleep_efficiency" in wearable:
            eff_score = max(0, min(100, wearable["sleep_efficiency"] * 100))
            obj_components.append(eff_score)
        if "resting_hr" in wearable:
            # RHR: lower is better, scale 45-75 -> 100-0
            rhr_score = max(0, min(100, (75 - wearable["resting_hr"]) / 30 * 100))
            obj_components.append(rhr_score)

        objective = sum(obj_components) / max(len(obj_components), 1) if obj_components else 50.0

        # Subjective score (0-100) from check-in
        if checkin:
            sub_vals = []
            if checkin.energy is not None:
                sub_vals.append(checkin.energy * 10)
            if checkin.mood is not None:
                sub_vals.append(checkin.mood * 10)
            if checkin.stress is not None:
                sub_vals.append((10 - checkin.stress) * 10)  # invert stress
            if checkin.sleep_quality is not None:
                sub_vals.append(checkin.sleep_quality * 10)
            subjective = sum(sub_vals) / max(len(sub_vals), 1) if sub_vals else 50.0
        else:
            subjective = 50.0

        composite = round(0.5 * objective + 0.5 * subjective, 1)

        # Contributing factors
        factors = []
        if "hrv_rmssd" in wearable:
            factors.append({
                "metric_key": "hrv_rmssd",
                "z_score": round((wearable["hrv_rmssd"] - 45) / 9, 2),
                "weight": 0.3,
                "direction": "higher_better",
                "label": "HRV",
            })
        if "sleep_efficiency" in wearable:
            factors.append({
                "metric_key": "sleep_efficiency",
                "z_score": round((wearable["sleep_efficiency"] - 0.85) / 0.05, 2),
                "weight": 0.25,
                "direction": "higher_better",
                "label": "Sleep Efficiency",
            })
        if checkin and checkin.energy is not None:
            factors.append({
                "metric_key": "energy",
                "z_score": round((checkin.energy - 7) / 2, 2),
                "weight": 0.25,
                "direction": "higher_better",
                "label": "Energy",
            })

        ws = WellnessScore(
            user_id=user_id,
            score_date=score_date,
            score=max(0, min(100, composite)),
            objective_score=round(objective, 1),
            subjective_score=round(subjective, 1),
            contributing_factors_json=factors,
            computed_at=datetime(score_date.year, score_date.month, score_date.day, 8, 0),
        )
        db.add(ws)

    print(f"    -> {TOTAL_DAYS} scores")


def seed_trust_score(db, user_id: int) -> None:
    """Single trust score for demo user."""
    db.add(TrustScore(
        user_id=user_id,
        score=72.0,
        data_coverage_score=85.0,
        adherence_score=85.0,
        evaluation_success_rate=100.0,
        stability_score=60.0,
        last_updated_at=datetime.utcnow(),
    ))


def seed_personal_health_model(db, user_id: int) -> None:
    """Single personal health model."""
    db.add(PersonalHealthModel(
        user_id=user_id,
        baselines_json={
            "sleep_duration": {"mean": 7.2, "std": 0.6},
            "sleep_duration_minutes": {"mean": 432, "std": 38},
            "hrv_rmssd": {"mean": 45.0, "std": 9.0},
            "hrv_rmssd_ms": {"mean": 45.0, "std": 9.0},
            "resting_hr": {"mean": 58.0, "std": 4.0},
            "resting_heart_rate_bpm": {"mean": 58.0, "std": 4.0},
            "sleep_efficiency": {"mean": 0.85, "std": 0.05},
            "subjective_energy": {"mean": 3.5, "std": 0.7},
        },
        sensitivities_json={
            "magnesium_glycinate": {
                "sleep_duration": {"effect_size": 0.62, "confidence": 0.82},
                "hrv_rmssd": {"effect_size": 0.45, "confidence": 0.58},
            },
            "late_caffeine": {
                "sleep_quality": {"effect_size": -0.55, "confidence": 0.75},
            },
        },
        drivers_json={
            "primary": ["magnesium_glycinate", "late_caffeine"],
            "secondary": ["stress_variability", "exercise_consistency"],
        },
        response_patterns_json={
            "lagged_effects": {
                "magnesium_glycinate": {"sleep_duration": 2, "hrv_rmssd": 3},
                "late_caffeine": {"sleep_quality": 0},
            },
        },
        confidence_score=68.0,
        data_coverage=78.0,
        model_version="v1",
    ))


# ─── Tier 3: Interventions & Experiments ─────────────────────

def seed_intervention(db, user_id: int) -> Intervention:
    """Create magnesium glycinate intervention."""
    intervention = Intervention(
        user_id=user_id,
        key="magnesium_glycinate",
        name="Magnesium Glycinate 400mg",
        category="supplement",
        dosage="400mg",
        schedule="Before bed, daily",
        notes="Magnesium glycinate chosen for sleep support. Well-absorbed form.",
        safety_risk_level="low",
        safety_evidence_grade="B",
        safety_boundary="experiment",
        safety_issues_json=json.dumps([]),
        safety_notes="Well-tolerated. Monitor for GI effects. Stop if diarrhea persists.",
        created_at=datetime.utcnow(),
    )
    db.add(intervention)
    return intervention


def seed_protocol(db, user_id: int, intervention_id: int) -> Protocol:
    """Create protocol wrapping the magnesium intervention."""
    protocol = Protocol(
        user_id=user_id,
        title="Magnesium Sleep Experiment Protocol",
        description="Test whether magnesium glycinate 400mg before bed improves sleep duration and quality.",
        status="completed",
        version=1,
        interventions_json=json.dumps([intervention_id]),
        safety_summary_json=json.dumps({
            "blocked": [],
            "warnings": ["Monitor for GI effects"],
            "boundary": "experiment",
            "risk_level": "low",
        }),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(protocol)
    return protocol


def seed_experiment(db, user_id: int, intervention_id: int, protocol_id: int, start_date: datetime) -> Experiment:
    """Create completed experiment."""
    exp = Experiment(
        user_id=user_id,
        intervention_id=intervention_id,
        protocol_id=protocol_id,
        hypothesis="Magnesium glycinate 400mg before bed improves sleep duration and efficiency",
        primary_metric_key="sleep_duration",
        expected_direction="up",
        baseline_window_days=14,
        intervention_window_days=30,
        status="completed",
        started_at=start_date + timedelta(days=EXPERIMENT_START),
        ended_at=start_date + timedelta(days=EXPERIMENT_END),
    )
    db.add(exp)
    return exp


def seed_adherence_events(db, user_id: int, experiment_id: int, intervention_id: int, start_date: datetime, rng) -> None:
    """30 adherence events for experiment period."""
    print("  Seeding AdherenceEvents...")
    count = 0
    missed_days = set(rng.choice(range(30), size=5, replace=False))

    for i in range(30):
        taken = i not in missed_days
        ae = AdherenceEvent(
            user_id=user_id,
            experiment_id=experiment_id,
            intervention_id=intervention_id,
            taken=taken,
            dose="400mg" if taken else None,
            dose_unit="mg" if taken else None,
            notes="Missed dose" if not taken else None,
            timestamp=start_date + timedelta(days=EXPERIMENT_START + i, hours=22),
        )
        db.add(ae)
        count += 1
    print(f"    -> {count} events ({30 - len(missed_days)} taken, {len(missed_days)} missed)")


def seed_evaluation_result(db, user_id: int, experiment_id: int) -> EvaluationResult:
    """Create evaluation for completed experiment."""
    ev = EvaluationResult(
        user_id=user_id,
        experiment_id=experiment_id,
        metric_key="sleep_duration",
        verdict="helpful",
        summary="Sleep duration increased by approximately 35 minutes during the intervention period. "
                "Effect size (Cohen's d) of 0.62 indicates a medium-to-large effect. "
                "Adherence was 83%, and data coverage was 87%.",
        baseline_mean=6.42,
        baseline_std=0.58,
        intervention_mean=7.01,
        intervention_std=0.45,
        delta=0.59,
        percent_change=9.2,
        effect_size=0.62,
        coverage=0.87,
        adherence_rate=0.83,
        pre_mean=6.42,
        post_mean=7.01,
        data_coverage=0.87,
        confidence=0.78,
        details_json={
            "method": "welch_t_test",
            "p_value": 0.008,
            "power": 0.82,
            "baseline_days": 14,
            "intervention_days": 30,
        },
        created_at=datetime.utcnow(),
    )
    db.add(ev)
    return ev


# ─── Tier 4: Insights & Narratives ──────────────────────────

def seed_insights(db, user_id: int, start_date: datetime) -> list:
    """7 insights spanning the timeline."""
    print("  Seeding Insights...")
    insights_data = [
        (15, "trend", "Sleep baseline established",
         "Your sleep duration baseline has been established at 7.2 hours with normal variation. The system now has enough data to detect meaningful changes.",
         0.85, {"metric_key": "sleep_duration", "domain_key": "sleep", "baseline_mean": 7.2, "baseline_std": 0.6, "claim_level": 3, "n_points": 15}),

        (35, "trend", "HRV declining trend detected",
         "Your heart rate variability has been declining over the past 5 days, dropping from 45ms to 38ms. This is associated with your elevated stress levels.",
         0.78, {"metric_key": "hrv_rmssd", "domain_key": "stress_nervous_system", "baseline_mean": 45.0, "recent_mean": 38.0, "z_score": -0.78, "claim_level": 2}),

        (40, "dysfunction", "Sleep efficiency degradation",
         "Your sleep efficiency has dropped to 78%, below your personal baseline of 85%. This coincides with elevated stress and increased late caffeine intake.",
         0.72, {"metric_key": "sleep_efficiency", "domain_key": "sleep", "baseline_mean": 0.85, "recent_mean": 0.78, "z_score": -1.4, "claim_level": 2}),

        (55, "correlation", "Magnesium associated with improved sleep onset",
         "Since starting magnesium glycinate, nights with supplementation show approximately 15 minutes shorter time to sleep onset compared to nights without.",
         0.65, {"metric_key": "sleep_duration", "domain_key": "sleep", "exposure_key": "magnesium_glycinate", "effect_size": 0.45, "claim_level": 2}),

        (70, "trend", "Sleep metrics recovering to baseline",
         "Your sleep duration has returned to pre-stress levels and appears to be stabilizing. HRV is also showing an upward trend.",
         0.82, {"metric_key": "sleep_duration", "domain_key": "sleep", "baseline_mean": 7.2, "recent_mean": 7.4, "z_score": 0.33, "claim_level": 3}),

        (75, "correlation", "Experiment evaluation: magnesium glycinate helpful",
         "Your magnesium glycinate experiment has been evaluated. Sleep duration improved by 9.2% with a medium effect size (d=0.62). The system considers this intervention helpful.",
         0.88, {"metric_key": "sleep_duration", "domain_key": "sleep", "experiment_id": 1, "verdict": "helpful", "effect_size": 0.62, "claim_level": 4}),

        (80, "trend", "HRV stabilized above baseline",
         "Your HRV has stabilized at approximately 50ms, above your original baseline of 45ms. This suggests improved autonomic recovery.",
         0.80, {"metric_key": "hrv_rmssd", "domain_key": "stress_nervous_system", "baseline_mean": 45.0, "recent_mean": 50.0, "z_score": 0.56, "claim_level": 3}),
    ]

    insights = []
    for day_offset, itype, title, desc, conf, meta in insights_data:
        insight = Insight(
            user_id=user_id,
            insight_type=itype,
            title=title,
            description=desc,
            confidence_score=conf,
            generated_at=start_date + timedelta(days=day_offset),
            metadata_json=json.dumps(meta),
        )
        db.add(insight)
        insights.append(insight)

    print(f"    -> {len(insights)} insights")
    return insights


def seed_narratives(db, user_id: int, start_date: date) -> None:
    """3 narratives at key points in the story."""
    print("  Seeding Narratives...")
    narratives_data = [
        {
            "period_type": "daily",
            "period_start": start_date + timedelta(days=29),
            "period_end": start_date + timedelta(days=29),
            "title": "Baseline period complete",
            "summary": "After 30 days of tracking, your baselines have been established. Sleep duration averages 7.2 hours with good efficiency (85%). HRV is stable at 45ms. No concerning patterns detected.",
            "key_points": [
                "Sleep duration baseline: 7.2 hours (stable)",
                "HRV baseline: 45ms (normal range)",
                "No significant trends or anomalies detected",
            ],
            "drivers": [],
            "actions": [{"action": "Continue tracking", "rationale": "Baselines established, ready for deeper analysis", "safety": "No concerns"}],
            "risks": [],
        },
        {
            "period_type": "daily",
            "period_start": start_date + timedelta(days=59),
            "period_end": start_date + timedelta(days=59),
            "title": "Mid-experiment: early signs of improvement",
            "summary": "Two weeks into the magnesium glycinate experiment. Sleep duration is showing gradual improvement from the stress-period low of 6.2 hours toward 6.8 hours. HRV is slowly recovering. Adherence is at 85%.",
            "key_points": [
                "Sleep duration improving: 6.2h -> 6.8h",
                "HRV recovering: 38ms -> 42ms",
                "Magnesium adherence: 85%",
                "Stress levels decreasing",
            ],
            "drivers": [{"metric_key": "sleep_duration", "why": "Magnesium supplementation and stress reduction", "evidence": "d=0.45, confidence=0.65"}],
            "actions": [{"action": "Continue magnesium protocol", "rationale": "Positive trend, maintain adherence", "safety": "No adverse effects reported"}],
            "risks": [{"risk": "Effect may plateau", "guidance": "Continue for full 30-day intervention window"}],
        },
        {
            "period_type": "daily",
            "period_start": start_date + timedelta(days=TOTAL_DAYS - 1),
            "period_end": start_date + timedelta(days=TOTAL_DAYS - 1),
            "title": "Recovery complete, new patterns learned",
            "summary": "Your health metrics have stabilized above pre-stress baselines. The magnesium glycinate experiment was evaluated as helpful (d=0.62). Sleep is now averaging 7.5 hours with 88% efficiency. HRV has stabilized at 50ms.",
            "key_points": [
                "Sleep duration: 7.5h (above baseline of 7.2h)",
                "Sleep efficiency: 88% (above baseline of 85%)",
                "HRV: 50ms (above baseline of 45ms)",
                "Magnesium experiment: HELPFUL (d=0.62)",
            ],
            "drivers": [
                {"metric_key": "sleep_duration", "why": "Magnesium glycinate supplementation", "evidence": "d=0.62, p=0.008"},
                {"metric_key": "hrv_rmssd", "why": "Improved sleep and stress recovery", "evidence": "d=0.45, confidence=0.58"},
            ],
            "actions": [
                {"action": "Continue magnesium glycinate", "rationale": "Demonstrated benefit for sleep", "safety": "Well-tolerated, no adverse effects"},
            ],
            "risks": [
                {"risk": "Monitor for tolerance effects", "guidance": "Re-evaluate in 60 days"},
            ],
        },
    ]

    for n in narratives_data:
        db.add(Narrative(
            user_id=user_id,
            period_type=n["period_type"],
            period_start=n["period_start"],
            period_end=n["period_end"],
            title=n["title"],
            summary=n["summary"],
            key_points_json=n["key_points"],
            drivers_json=n["drivers"],
            actions_json=n["actions"],
            risks_json=n["risks"],
            metadata_json={"source": "seed_demo"},
        ))
    print(f"    -> {len(narratives_data)} narratives")


def seed_insight_summaries(db, user_id: int) -> None:
    """Weekly summaries for last 4 weeks."""
    print("  Seeding InsightSummaries...")
    today = date.today()
    summaries = [
        {
            "offset_weeks": 3,
            "headline": "Stress period: sleep and HRV declining",
            "narrative": "This week saw significant sleep disruption with HRV dropping to 38ms. Work stress is the likely driver.",
            "confidence": 70,
        },
        {
            "offset_weeks": 2,
            "headline": "Experiment started: magnesium glycinate",
            "narrative": "Started magnesium glycinate 400mg before bed. Initial data shows no significant change yet.",
            "confidence": 55,
        },
        {
            "offset_weeks": 1,
            "headline": "Positive trend: sleep improving",
            "narrative": "Sleep duration and efficiency are both trending upward. Magnesium adherence at 85%. HRV recovering.",
            "confidence": 75,
        },
        {
            "offset_weeks": 0,
            "headline": "Stabilization: metrics above baseline",
            "narrative": "All key metrics have stabilized above pre-stress baselines. Experiment evaluation: magnesium helpful (d=0.62).",
            "confidence": 85,
        },
    ]

    for s in summaries:
        summary_date = today - timedelta(weeks=s["offset_weeks"])
        db.add(InsightSummary(
            user_id=user_id,
            period="weekly",
            summary_date=summary_date,
            headline=s["headline"],
            narrative=s["narrative"],
            key_metrics=["sleep_duration", "hrv_rmssd", "sleep_efficiency"],
            drivers=["magnesium_glycinate", "stress"],
            interventions=["magnesium_glycinate"],
            outcomes=["sleep_improving", "hrv_recovering"],
            confidence=s["confidence"],
        ))
    print(f"    -> {len(summaries)} summaries")


# ─── Tier 5: Causal & Pattern Learning ──────────────────────

def seed_driver_findings(db, user_id: int, start_date: date) -> None:
    """3 driver findings."""
    print("  Seeding DriverFindings...")
    findings = [
        {
            "exposure_type": "intervention", "exposure_key": "magnesium_glycinate",
            "metric_key": "sleep_duration", "lag_days": 1, "direction": "improves",
            "effect_size": 0.62, "confidence": 0.78, "coverage": 0.87,
            "n_exposure_days": 25, "n_total_days": 30,
        },
        {
            "exposure_type": "intervention", "exposure_key": "magnesium_glycinate",
            "metric_key": "hrv_rmssd", "lag_days": 2, "direction": "improves",
            "effect_size": 0.45, "confidence": 0.65, "coverage": 0.82,
            "n_exposure_days": 25, "n_total_days": 30,
        },
        {
            "exposure_type": "behavior", "exposure_key": "late_caffeine",
            "metric_key": "sleep_quality", "lag_days": 0, "direction": "worsens",
            "effect_size": -0.55, "confidence": 0.71, "coverage": 0.88,
            "n_exposure_days": 12, "n_total_days": 30,
        },
    ]
    ws = start_date + timedelta(days=EXPERIMENT_START)
    we = start_date + timedelta(days=EXPERIMENT_END)
    for f in findings:
        db.add(DriverFinding(
            user_id=user_id, window_start=ws, window_end=we,
            created_at=datetime.utcnow(), **f,
        ))
    print(f"    -> {len(findings)} findings")


def seed_personal_drivers(db, user_id: int) -> None:
    """2 personal drivers."""
    print("  Seeding PersonalDrivers...")
    drivers = [
        {
            "driver_type": "supplement", "driver_key": "magnesium_glycinate",
            "outcome_metric": "sleep_duration", "lag_days": 1,
            "effect_size": 0.62, "direction": "positive",
            "variance_explained": 0.18, "confidence": 0.78, "stability": 0.72,
            "sample_size": 30,
        },
        {
            "driver_type": "behavior", "driver_key": "late_caffeine",
            "outcome_metric": "sleep_duration", "lag_days": 0,
            "effect_size": -0.55, "direction": "negative",
            "variance_explained": 0.12, "confidence": 0.71, "stability": 0.68,
            "sample_size": 30,
        },
    ]
    for d in drivers:
        db.add(PersonalDriver(user_id=user_id, **d))
    print(f"    -> {len(drivers)} drivers")


def seed_personal_patterns(db, user_id: int, start_date: datetime) -> None:
    """3 patterns with varying statuses."""
    print("  Seeding PersonalPatterns...")
    patterns = [
        PersonalPattern(
            user_id=user_id,
            pattern_type="correlation",
            input_signals_json=["late_caffeine"],
            output_signal="hrv_rmssd",
            relationship_json={"r": -0.62, "p_value": 0.003, "direction": "negative"},
            times_observed=8, times_confirmed=6, current_confidence=0.78,
            first_detected=start_date + timedelta(days=35),
            last_confirmed=start_date + timedelta(days=80),
            typical_lag_hours=12.0,
            status="confirmed", user_acknowledged=True,
        ),
        PersonalPattern(
            user_id=user_id,
            pattern_type="response",
            input_signals_json=["magnesium_glycinate"],
            output_signal="sleep_duration",
            relationship_json={"lag_hours": 48, "effect_size": 0.62},
            times_observed=5, times_confirmed=4, current_confidence=0.82,
            first_detected=start_date + timedelta(days=55),
            last_confirmed=start_date + timedelta(days=75),
            typical_lag_hours=48.0,
            status="confirmed", user_acknowledged=True,
        ),
        PersonalPattern(
            user_id=user_id,
            pattern_type="cycle",
            input_signals_json=["weekly_rhythm"],
            output_signal="subjective_energy",
            relationship_json={"period_days": 7, "phase": "peak_monday_dip_thursday"},
            times_observed=4, times_confirmed=2, current_confidence=0.45,
            first_detected=start_date + timedelta(days=20),
            last_confirmed=start_date + timedelta(days=60),
            typical_lag_hours=None,
            status="hypothesis", user_acknowledged=False,
        ),
    ]
    for p in patterns:
        db.add(p)
    print(f"    -> {len(patterns)} patterns")


def seed_causal_memory(db, user_id: int, evaluation_id: int, start_date: datetime) -> None:
    """4 causal memory entries."""
    print("  Seeding CausalMemory...")
    memories = [
        CausalMemory(
            user_id=user_id,
            driver_type="supplement", driver_key="magnesium_glycinate",
            metric_key="sleep_duration", direction="improves",
            avg_effect_size=0.62, confidence=0.82, evidence_count=3,
            first_seen_at=start_date + timedelta(days=55),
            last_confirmed_at=start_date + timedelta(days=75),
            status="confirmed",
            supporting_evaluations_json=[{"eval_id": evaluation_id, "contribution": 0.6}],
        ),
        CausalMemory(
            user_id=user_id,
            driver_type="supplement", driver_key="magnesium_glycinate",
            metric_key="hrv_rmssd", direction="improves",
            avg_effect_size=0.45, confidence=0.58, evidence_count=2,
            first_seen_at=start_date + timedelta(days=60),
            last_confirmed_at=start_date + timedelta(days=75),
            status="tentative",
            supporting_evaluations_json=[{"eval_id": evaluation_id, "contribution": 0.4}],
        ),
        CausalMemory(
            user_id=user_id,
            driver_type="behavior", driver_key="late_caffeine",
            metric_key="sleep_quality", direction="worsens",
            avg_effect_size=-0.55, confidence=0.75, evidence_count=4,
            first_seen_at=start_date + timedelta(days=35),
            last_confirmed_at=start_date + timedelta(days=80),
            status="confirmed",
            supporting_evaluations_json=[],
        ),
        CausalMemory(
            user_id=user_id,
            driver_type="behavior", driver_key="alcohol_evening",
            metric_key="hrv_rmssd", direction="worsens",
            avg_effect_size=-0.35, confidence=0.35, evidence_count=1,
            first_seen_at=start_date + timedelta(days=40),
            last_confirmed_at=None,
            status="deprecated",
            supporting_evaluations_json=[],
        ),
    ]
    for m in memories:
        db.add(m)
    print(f"    -> {len(memories)} memories")


# ─── Tier 6: Graphs, Notifications, Audit ────────────────────

def seed_causal_graph(db, user_id: int) -> None:
    """Causal graph edges and snapshot."""
    print("  Seeding CausalGraph...")
    edges = [
        {"driver_key": "magnesium_glycinate", "driver_kind": "intervention", "target_metric_key": "sleep_duration",
         "lag_days": 1, "direction": "up", "effect_size": 0.62, "confidence": 0.78, "coverage": 0.87,
         "confounder_penalty": 0.05, "interaction_boost": 0.0, "score": 0.73},
        {"driver_key": "magnesium_glycinate", "driver_kind": "intervention", "target_metric_key": "hrv_rmssd",
         "lag_days": 2, "direction": "up", "effect_size": 0.45, "confidence": 0.65, "coverage": 0.82,
         "confounder_penalty": 0.08, "interaction_boost": 0.0, "score": 0.57},
        {"driver_key": "late_caffeine", "driver_kind": "behavior", "target_metric_key": "sleep_quality",
         "lag_days": 0, "direction": "down", "effect_size": 0.55, "confidence": 0.71, "coverage": 0.88,
         "confounder_penalty": 0.03, "interaction_boost": 0.0, "score": 0.68},
        {"driver_key": "sleep_duration", "driver_kind": "metric", "target_metric_key": "subjective_energy",
         "lag_days": 0, "direction": "up", "effect_size": 0.72, "confidence": 0.85, "coverage": 0.95,
         "confounder_penalty": 0.02, "interaction_boost": 0.0, "score": 0.83},
        {"driver_key": "hrv_rmssd", "driver_kind": "metric", "target_metric_key": "subjective_energy",
         "lag_days": 0, "direction": "up", "effect_size": 0.48, "confidence": 0.70, "coverage": 0.90,
         "confounder_penalty": 0.05, "interaction_boost": 0.0, "score": 0.65},
    ]
    for e in edges:
        db.add(CausalGraphEdge(
            user_id=user_id, details_json=json.dumps({"source": "seed_demo"}),
            generated_at=datetime.utcnow(), **e,
        ))

    # Snapshot
    snapshot_data = {
        "nodes": [
            {"id": "magnesium_glycinate", "kind": "intervention", "label": "Magnesium Glycinate"},
            {"id": "late_caffeine", "kind": "behavior", "label": "Late Caffeine"},
            {"id": "sleep_duration", "kind": "metric", "label": "Sleep Duration"},
            {"id": "sleep_quality", "kind": "metric", "label": "Sleep Quality"},
            {"id": "hrv_rmssd", "kind": "metric", "label": "HRV"},
            {"id": "subjective_energy", "kind": "metric", "label": "Energy"},
        ],
        "edges": [{"from": e["driver_key"], "to": e["target_metric_key"], "score": e["score"]} for e in edges],
    }
    db.add(CausalGraphSnapshot(
        user_id=user_id,
        generated_at=datetime.utcnow(),
        snapshot_json=json.dumps(snapshot_data),
    ))
    print(f"    -> {len(edges)} edges + 1 snapshot")


def seed_explanation_edges(db, insight_ids: list) -> None:
    """Link insights to source data."""
    print("  Seeding ExplanationEdges...")
    if len(insight_ids) < 4:
        print("    -> skipped (not enough insights)")
        return

    edges = [
        ExplanationEdge(
            target_type="insight", target_id=insight_ids[0],
            source_type="metric", source_id=None,
            contribution_weight=1.0,
            description="Sleep duration data from wearable (30 days)",
        ),
        ExplanationEdge(
            target_type="insight", target_id=insight_ids[1],
            source_type="metric", source_id=None,
            contribution_weight=0.8,
            description="HRV trend data from wearable",
        ),
        ExplanationEdge(
            target_type="insight", target_id=insight_ids[3],
            source_type="checkin", source_id=None,
            contribution_weight=0.6,
            description="Daily check-in supplement logging",
        ),
        ExplanationEdge(
            target_type="insight", target_id=insight_ids[5] if len(insight_ids) > 5 else insight_ids[-1],
            source_type="evaluation", source_id=1,
            contribution_weight=0.9,
            description="Experiment evaluation result",
        ),
    ]
    for e in edges:
        db.add(e)
    print(f"    -> {len(edges)} edges")


def seed_inbox_items(db, user_id: int, start_date: datetime) -> None:
    """5 inbox items spanning the timeline."""
    print("  Seeding InboxItems...")
    items = [
        {"category": "system", "title": "Welcome to your health dashboard",
         "body": "Your account is set up and ready. Start by connecting a wearable device and completing your first daily check-in.",
         "offset_days": 0, "is_read": True},
        {"category": "insight", "title": "Baseline period complete",
         "body": "After 30 days of tracking, your personal baselines have been established. The system can now detect meaningful changes in your metrics.",
         "offset_days": 30, "is_read": True},
        {"category": "safety", "title": "Stress pattern detected",
         "body": "Your HRV has declined significantly over the past week while stress scores are elevated. Consider prioritizing recovery.",
         "offset_days": 38, "is_read": True},
        {"category": "experiment", "title": "Experiment evaluation ready",
         "body": "Your magnesium glycinate experiment has completed its 30-day window. Results: sleep duration improved by 9.2% (d=0.62). Verdict: helpful.",
         "offset_days": 75, "is_read": False},
        {"category": "insight", "title": "Weekly summary available",
         "body": "Your weekly health summary is ready. Key highlight: all metrics have stabilized above pre-stress baselines.",
         "offset_days": TOTAL_DAYS - 1, "is_read": False},
    ]
    for item in items:
        db.add(InboxItem(
            user_id=user_id,
            category=item["category"],
            title=item["title"],
            body=item["body"],
            is_read=item["is_read"],
            created_at=start_date + timedelta(days=item["offset_days"]),
        ))
    print(f"    -> {len(items)} items")


def seed_notification_outbox(db, user_id: int) -> None:
    """3 dispatched notifications."""
    for i, (ntype, dedupe) in enumerate([
        ("baseline_complete", f"baseline_complete:{user_id}"),
        ("stress_alert", f"stress_alert:{user_id}"),
        ("experiment_result", f"experiment_result:{user_id}:1"),
    ]):
        db.add(NotificationOutbox(
            user_id=user_id,
            channel="inbox",
            notification_type=ntype,
            dedupe_key=dedupe,
            payload_json=json.dumps({"source": "seed_demo"}),
            is_dispatched=True,
            dispatched_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        ))


def seed_audit_events(db, user_id: int, entity_ids: dict) -> None:
    """5 audit events for key decisions."""
    print("  Seeding AuditEvents...")
    events = [
        {
            "entity_type": "insight", "entity_id": entity_ids.get("insight", 1),
            "decision_type": "created", "decision_reason": "Trend detected: HRV declining",
            "source_metrics": json.dumps(["hrv_rmssd"]),
            "detectors_used": json.dumps(["trend_detector"]),
            "thresholds_crossed": json.dumps(["z_score > 1.5"]),
            "safety_checks_applied": json.dumps(["red_flag_check: passed"]),
        },
        {
            "entity_type": "experiment", "entity_id": entity_ids.get("experiment", 1),
            "decision_type": "created", "decision_reason": "User initiated magnesium experiment",
            "safety_checks_applied": json.dumps(["safety_gate: low_risk", "boundary: experiment"]),
        },
        {
            "entity_type": "evaluation", "entity_id": entity_ids.get("evaluation", 1),
            "decision_type": "created", "decision_reason": "Experiment completed, evaluation triggered",
            "source_metrics": json.dumps(["sleep_duration"]),
            "detectors_used": json.dumps(["welch_t_test", "effect_size_calculator"]),
        },
        {
            "entity_type": "insight", "entity_id": entity_ids.get("insight", 1),
            "decision_type": "suppressed", "decision_reason": "Insufficient confidence (0.42 < 0.5 threshold)",
            "safety_checks_applied": json.dumps(["claim_policy: suppressed"]),
        },
        {
            "entity_type": "intervention", "entity_id": entity_ids.get("intervention", 1),
            "decision_type": "created", "decision_reason": "Safety evaluation completed: low risk, grade B evidence",
            "safety_checks_applied": json.dumps(["safety_gate: passed", "evidence_grade: B", "boundary: experiment"]),
        },
    ]
    for e in events:
        db.add(AuditEvent(user_id=user_id, created_at=datetime.utcnow(), **e))
    print(f"    -> {len(events)} audit events")


def seed_decision_signals(db, user_id: int, insight_ids: list) -> None:
    """3 decision signals at different confidence levels."""
    print("  Seeding DecisionSignals...")
    if not insight_ids:
        return

    signals = [
        DecisionSignal(
            user_id=user_id,
            source_type="insight", source_id=insight_ids[0],
            level=1, level_name="observational",
            confidence=0.55, evidence_count=1,
            confidence_explanation_json={"data_coverage": 0.8, "effect_size": None, "consistency": "single_observation"},
            allowed_actions=["monitor"],
            language_constraints={"must_use": ["observed", "appears"], "must_not_use": ["causes", "proves"]},
        ),
        DecisionSignal(
            user_id=user_id,
            source_type="insight", source_id=insight_ids[3] if len(insight_ids) > 3 else insight_ids[-1],
            level=2, level_name="correlational",
            confidence=0.65, evidence_count=2,
            confidence_explanation_json={"data_coverage": 0.87, "effect_size": 0.45, "consistency": "moderate"},
            allowed_actions=["monitor", "suggest_experiment"],
            language_constraints={"must_use": ["associated with", "correlated"], "must_not_use": ["causes", "proves"]},
        ),
        DecisionSignal(
            user_id=user_id,
            source_type="insight", source_id=insight_ids[5] if len(insight_ids) > 5 else insight_ids[-1],
            level=4, level_name="evaluated",
            confidence=0.82, evidence_count=3,
            last_confirmed_at=datetime.utcnow(),
            confidence_explanation_json={"data_coverage": 0.87, "adherence_rate": 0.83, "effect_size": 0.62, "p_value": 0.008},
            allowed_actions=["monitor", "continue_protocol", "suggest_similar"],
            language_constraints={"must_use": ["demonstrated", "supported by evidence"], "must_not_use": ["proves", "guarantees"]},
        ),
    ]
    for s in signals:
        db.add(s)
    print(f"    -> {len(signals)} signals")


# ─── Main Orchestrator ──────────────────────────────────────

def main():
    """Orchestrate all seeding in correct FK order."""
    print("=" * 60)
    print("  AI Health Platform: Comprehensive Demo Seed")
    print("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    rng = np.random.default_rng(SEED)
    factory = HealthDataFactory(profile=PersonalProfile(), seed=SEED)

    start_dt = datetime.utcnow() - timedelta(days=TOTAL_DAYS)
    start_d = start_dt.date()

    try:
        # Step 0: Clear existing demo data
        clear_demo_data(db)

        # ── Tier 0: Foundation ──
        print("\n[Tier 0] Foundation")
        user = seed_user(db)
        seed_consent(db, user.id)
        seed_provider_token(db, user.id)
        seed_data_provenance(db, user.id)
        db.commit()

        # ── Tier 1: Raw Time Series ──
        print("\n[Tier 1] Raw Time Series")
        health_data = seed_health_data_points(db, user.id, start_dt, factory, rng)
        seed_wearable_samples(db, user.id, start_dt, health_data)
        checkins = seed_daily_checkins(db, user.id, start_d, rng)
        seed_symptoms(db, user.id, start_dt)
        seed_lab_results(db, user.id, start_dt)
        db.commit()

        # ── Tier 2: Derived Analytics ──
        print("\n[Tier 2] Derived Analytics")
        seed_baselines(db, user.id, health_data)
        seed_wellness_scores(db, user.id, start_d, checkins, health_data)
        seed_trust_score(db, user.id)
        seed_personal_health_model(db, user.id)
        db.commit()

        # ── Tier 3: Interventions & Experiments ──
        print("\n[Tier 3] Interventions & Experiments")
        intervention = seed_intervention(db, user.id)
        db.flush()
        protocol = seed_protocol(db, user.id, intervention.id)
        db.flush()
        experiment = seed_experiment(db, user.id, intervention.id, protocol.id, start_dt)
        db.flush()
        seed_adherence_events(db, user.id, experiment.id, intervention.id, start_dt, rng)
        evaluation = seed_evaluation_result(db, user.id, experiment.id)
        db.flush()
        db.commit()
        print(f"  Intervention #{intervention.id}, Protocol #{protocol.id}, Experiment #{experiment.id}, Eval #{evaluation.id}")

        # ── Tier 4: Insights & Narratives ──
        print("\n[Tier 4] Insights & Narratives")
        insights = seed_insights(db, user.id, start_dt)
        db.flush()
        insight_ids = [i.id for i in insights]
        seed_narratives(db, user.id, start_d)
        seed_insight_summaries(db, user.id)
        db.commit()

        # ── Tier 5: Causal & Pattern Learning ──
        print("\n[Tier 5] Causal & Pattern Learning")
        seed_driver_findings(db, user.id, start_d)
        seed_personal_drivers(db, user.id)
        seed_personal_patterns(db, user.id, start_dt)
        seed_causal_memory(db, user.id, evaluation.id, start_dt)
        db.commit()

        # ── Tier 6: Graphs, Notifications, Audit ──
        print("\n[Tier 6] Graphs, Notifications, Audit")
        seed_causal_graph(db, user.id)
        seed_explanation_edges(db, insight_ids)
        seed_inbox_items(db, user.id, start_dt)
        seed_notification_outbox(db, user.id)
        seed_audit_events(db, user.id, {
            "insight": insight_ids[0] if insight_ids else 1,
            "experiment": experiment.id,
            "evaluation": evaluation.id,
            "intervention": intervention.id,
        })
        seed_decision_signals(db, user.id, insight_ids)
        db.commit()

        # ── Summary ──
        print("\n" + "=" * 60)
        print("  SEEDING COMPLETE")
        print("=" * 60)
        print(f"  User:              {user.email} (id={user.id})")
        print(f"  Time range:        {TOTAL_DAYS} days ({start_d} to {date.today()})")
        print(f"  HealthDataPoints:  ~{len(health_data)} (+ aliases)")
        print(f"  DailyCheckIns:     {len(checkins)}")
        print(f"  Insights:          {len(insights)}")
        print(f"  Narratives:        3")
        print(f"  Experiment:        #{experiment.id} (magnesium glycinate -> {evaluation.verdict})")
        print(f"  CausalMemory:      4 entries")
        print(f"  Models seeded:     28")
        print(f"\n  Run: make backend && make frontend")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
