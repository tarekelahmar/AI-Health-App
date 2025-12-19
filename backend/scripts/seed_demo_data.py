#!/usr/bin/env python3
"""
Comprehensive demo data seeder for testing the insight loop.

Seeds data into the HealthDataPoint table (health_data) which is what
the insight loop's signal_builder reads from.

Usage:
    cd backend
    python -m scripts.seed_demo_data
    python -m scripts.seed_demo_data --scenario illness
    python -m scripts.seed_demo_data --user-id 1 --days 30 --scenario stress
"""
import argparse
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

from app.core.database import SessionLocal
from app.domain.models import User
from app.domain.models.health_data_point import HealthDataPoint
from app.domain.models.consent import Consent
from app.domain.models.baseline import Baseline


# ============================================================================
# SCENARIOS: Pre-defined health patterns for testing specific system behaviors
# ============================================================================

SCENARIOS = {
    "healthy_baseline": {
        "description": "30 days of normal health with natural variation",
        "modifiers": {},  # No modifications, just baseline
    },
    "sleep_debt": {
        "description": "Progressive sleep debt in recent days (0-6), detectable by change detector",
        "modifiers": {
            # Recent days (day 0 = today, day 1 = yesterday, etc.)
            0: {"sleep_duration": 0.65, "hrv_rmssd": 0.7, "energy": 0.6},
            1: {"sleep_duration": 0.7, "hrv_rmssd": 0.75, "energy": 0.65},
            2: {"sleep_duration": 0.75, "hrv_rmssd": 0.8, "energy": 0.7},
            3: {"sleep_duration": 0.8, "hrv_rmssd": 0.85, "energy": 0.75},
            4: {"sleep_duration": 0.85, "hrv_rmssd": 0.9, "energy": 0.8},
            5: {"sleep_duration": 0.9, "hrv_rmssd": 0.93, "energy": 0.85},
            6: {"sleep_duration": 0.95, "hrv_rmssd": 0.96, "energy": 0.9},
        },
    },
    "illness": {
        "description": "Acute illness in recent days (0-5), easily detectable",
        "modifiers": {
            # Recent days - acute phase
            0: {"hrv_rmssd": 0.55, "resting_hr": 1.25, "energy": 0.35, "sleep_efficiency": 0.75},
            1: {"hrv_rmssd": 0.6, "resting_hr": 1.2, "energy": 0.4, "sleep_efficiency": 0.8},
            2: {"hrv_rmssd": 0.65, "resting_hr": 1.18, "energy": 0.45, "sleep_efficiency": 0.82},
            3: {"hrv_rmssd": 0.7, "resting_hr": 1.15, "energy": 0.5, "sleep_efficiency": 0.85},
            4: {"hrv_rmssd": 0.8, "resting_hr": 1.1, "energy": 0.6, "sleep_efficiency": 0.88},
            5: {"hrv_rmssd": 0.9, "resting_hr": 1.05, "energy": 0.75, "sleep_efficiency": 0.93},
        },
    },
    "stress": {
        "description": "Elevated stress period in recent days (0-10)",
        "modifiers": {
            **{d: {"hrv_rmssd": 0.75, "stress": 1.4, "sleep_efficiency": 0.85, "energy": 0.8}
               for d in range(0, 11)},
        },
    },
    "improvement": {
        "description": "Gradual improvement over past two weeks (visible in trends)",
        "modifiers": {
            **{d: {
                "sleep_duration": 1.0 + (14 - d) * 0.015,  # Gets better as we approach today
                "sleep_efficiency": 1.0 + (14 - d) * 0.01,
                "hrv_rmssd": 1.0 + (14 - d) * 0.02,
                "energy": 1.0 + (14 - d) * 0.015,
            } for d in range(0, 15)},
        },
    },
}


# ============================================================================
# BASELINE VALUES: Personal baselines for synthetic user
# ============================================================================

BASELINES = {
    # Wearable metrics (objective)
    "sleep_duration": {"value": 420, "unit": "minutes", "noise": 0.1},  # 7 hours
    "sleep_efficiency": {"value": 85, "unit": "percent", "noise": 0.05},
    "resting_hr": {"value": 58, "unit": "bpm", "noise": 0.08},
    "hrv_rmssd": {"value": 45, "unit": "ms", "noise": 0.15},
    "steps": {"value": 8000, "unit": "count", "noise": 0.25},

    # Subjective metrics (user input)
    "sleep_quality": {"value": 3.5, "unit": "score_1_5", "noise": 0.15},
    "energy": {"value": 3.2, "unit": "score_1_5", "noise": 0.15},
    "stress": {"value": 2.5, "unit": "score_1_5", "noise": 0.2},
}


def create_baselines(db, user_id: int, window_days: int = 14, offset_days: int = 15):
    """
    Create baseline records for all metrics based on the seeded data.

    Uses data from `offset_days` to `offset_days + window_days` ago
    (i.e., the OLDER healthy data, not the recent potentially abnormal data).
    This is required for the insight loop to function - without baselines,
    all metrics are skipped.

    Args:
        db: Database session
        user_id: User ID
        window_days: Number of days to include in baseline computation
        offset_days: Start computing baseline this many days ago
                     (to skip recent abnormal data from scenarios)
    """
    import statistics

    print(f"\n📈 Computing baselines from days {offset_days} to {offset_days + window_days} ago...")
    print(f"   (Skipping recent {offset_days} days to use healthy baseline data)")

    baselines_created = 0
    baselines_updated = 0

    for metric_key in BASELINES.keys():
        # Get data points from the healthy period (older data)
        from datetime import datetime, timedelta
        start_date = datetime.utcnow() - timedelta(days=offset_days + window_days)
        end_date = datetime.utcnow() - timedelta(days=offset_days)

        points = db.query(HealthDataPoint).filter(
            HealthDataPoint.user_id == user_id,
            HealthDataPoint.metric_type == metric_key,
            HealthDataPoint.timestamp >= start_date,
            HealthDataPoint.timestamp <= end_date
        ).all()

        if len(points) < 5:
            print(f"   ⚠️  {metric_key}: insufficient data ({len(points)} points)")
            continue

        values = [p.value for p in points]
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0.1  # Fallback std

        # Check if baseline exists
        existing = db.query(Baseline).filter(
            Baseline.user_id == user_id,
            Baseline.metric_type == metric_key
        ).first()

        if existing:
            existing.mean = mean
            existing.std = std
            existing.window_days = window_days
            baselines_updated += 1
        else:
            baseline = Baseline(
                user_id=user_id,
                metric_type=metric_key,
                mean=mean,
                std=std,
                window_days=window_days
            )
            db.add(baseline)
            baselines_created += 1

        print(f"   ✅ {metric_key}: mean={mean:.2f}, std={std:.2f}")

    db.commit()
    print(f"\n   Created: {baselines_created}, Updated: {baselines_updated}")


def generate_value(
    metric_key: str,
    day_offset: int,
    scenario_modifiers: Dict[int, Dict[str, float]],
    seed: int = 42
) -> float:
    """Generate a realistic value for a metric on a given day."""
    random.seed(seed + day_offset + hash(metric_key))

    baseline = BASELINES[metric_key]
    base_value = baseline["value"]
    noise_level = baseline["noise"]

    # Add natural day-to-day variation
    noise = random.gauss(0, noise_level)
    value = base_value * (1 + noise)

    # Add weekly pattern (weekends slightly different)
    day_of_week = (datetime.utcnow() - timedelta(days=day_offset)).weekday()
    if day_of_week >= 5:  # Weekend
        if metric_key == "sleep_duration":
            value *= 1.05  # Sleep more on weekends
        elif metric_key == "steps":
            value *= 0.85  # Fewer steps on weekends

    # Apply scenario modifiers
    if day_offset in scenario_modifiers:
        modifier = scenario_modifiers[day_offset].get(metric_key, 1.0)
        value *= modifier

    # Clamp to valid ranges
    if metric_key == "sleep_efficiency":
        value = min(98, max(50, value))
    elif metric_key in ["sleep_quality", "energy", "stress"]:
        value = min(5, max(1, value))
    elif metric_key == "hrv_rmssd":
        value = max(15, value)
    elif metric_key == "resting_hr":
        value = min(100, max(40, value))
    elif metric_key == "steps":
        value = max(1000, value)
    elif metric_key == "sleep_duration":
        value = min(600, max(180, value))  # 3-10 hours in minutes

    return round(value, 2)


def seed_demo_data(
    user_id: Optional[int] = None,
    days: int = 30,
    scenario: str = "healthy_baseline",
    clear_existing: bool = False
):
    """
    Seed demo data into the HealthDataPoint table.

    This is what the insight loop reads from via signal_builder.py.
    """
    db = SessionLocal()

    try:
        print("🌱 Seeding demo data...")
        print(f"   Scenario: {scenario}")
        print(f"   Days: {days}")

        # Get scenario modifiers
        if scenario not in SCENARIOS:
            print(f"❌ Unknown scenario: {scenario}")
            print(f"   Available: {list(SCENARIOS.keys())}")
            return

        scenario_config = SCENARIOS[scenario]
        print(f"   Description: {scenario_config['description']}")
        modifiers = scenario_config["modifiers"]

        # ---- User ----
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                print(f"❌ User ID {user_id} not found")
                return
            print(f"✅ Using existing user (ID: {user.id})")
        else:
            # Create or get demo user
            user = db.query(User).filter(User.email == "demo@example.com").first()
            if user:
                print(f"✅ Found existing demo user (ID: {user.id})")
            else:
                user = User(
                    name="Demo User",
                    email="demo@example.com",
                    hashed_password="demo_hash_not_for_production",
                    created_at=datetime.utcnow(),
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"✅ Created new demo user (ID: {user.id})")

        # ---- Consent (required for insight generation) ----
        consent = db.query(Consent).filter(Consent.user_id == user.id).first()
        if not consent:
            consent = Consent(
                user_id=user.id,
                consent_version="1.0",
                understands_not_medical_advice=True,
                consents_to_data_analysis=True,
                understands_recommendations_experimental=True,
                understands_can_stop_anytime=True,
                onboarding_completed=True,
                onboarding_completed_at=datetime.utcnow(),
            )
            db.add(consent)
            db.commit()
            print(f"✅ Created consent record for user {user.id}")
        else:
            print(f"✅ Consent already exists for user {user.id}")

        # ---- Clear existing data if requested ----
        if clear_existing:
            deleted = db.query(HealthDataPoint).filter(
                HealthDataPoint.user_id == user.id
            ).delete()
            db.commit()
            print(f"🗑️  Cleared {deleted} existing health data points")

        # ---- Generate health data ----
        points_created = 0
        points_skipped = 0

        for day_offset in range(days):
            target_date = datetime.utcnow() - timedelta(days=day_offset)
            # Normalize to midnight for consistency
            target_timestamp = target_date.replace(hour=8, minute=0, second=0, microsecond=0)

            for metric_key, baseline in BASELINES.items():
                # Check if data point already exists for this day
                existing = db.query(HealthDataPoint).filter(
                    HealthDataPoint.user_id == user.id,
                    HealthDataPoint.metric_type == metric_key,
                    HealthDataPoint.timestamp >= target_timestamp - timedelta(hours=12),
                    HealthDataPoint.timestamp <= target_timestamp + timedelta(hours=12),
                ).first()

                if existing:
                    points_skipped += 1
                    continue

                # Generate value with scenario modifiers
                value = generate_value(metric_key, day_offset, modifiers)

                # Create health data point
                point = HealthDataPoint(
                    user_id=user.id,
                    metric_type=metric_key,
                    value=value,
                    unit=baseline["unit"],
                    timestamp=target_timestamp,
                    source="demo",
                )
                db.add(point)
                points_created += 1

        db.commit()

        print(f"\n📊 Results:")
        print(f"   Created: {points_created} data points")
        print(f"   Skipped: {points_skipped} (already existed)")
        print(f"   User ID: {user.id}")
        print(f"   Metrics: {list(BASELINES.keys())}")

        # Create baselines from the seeded data
        # Use 14-day window, computing from the "healthy" portion of data
        create_baselines(db, user.id, window_days=14)

        print(f"\n✅ Demo data seeded successfully!")
        print(f"\n🧪 Test the insight loop:")
        print(f"   curl -X POST 'http://localhost:8000/api/v1/insights/run?user_id={user.id}'")

        return user.id

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


def list_scenarios():
    """Print available scenarios."""
    print("\n📋 Available Scenarios:\n")
    for name, config in SCENARIOS.items():
        print(f"  {name}")
        print(f"    {config['description']}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo health data")
    parser.add_argument("--user-id", type=int, help="User ID to seed data for (creates demo user if not specified)")
    parser.add_argument("--days", type=int, default=30, help="Number of days of data to generate")
    parser.add_argument("--scenario", default="healthy_baseline",
                       choices=list(SCENARIOS.keys()),
                       help="Scenario to simulate")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before seeding")
    parser.add_argument("--list-scenarios", action="store_true", help="List available scenarios")

    args = parser.parse_args()

    if args.list_scenarios:
        list_scenarios()
    else:
        seed_demo_data(
            user_id=args.user_id,
            days=args.days,
            scenario=args.scenario,
            clear_existing=args.clear
        )
