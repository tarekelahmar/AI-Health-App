"""
Seed the development database with synthetic demo data for testing insights.

Run with:

    uvicorn app.main:app --reload

    python scripts/seed_demo_data.py
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from datetime import datetime, timedelta

from app.core.database import SessionLocal

from app.domain.repositories import (
    UserRepository,
    WearableRepository,
    LabResultRepository,
    HealthDataRepository,
    SymptomRepository,
)
from app.domain.models import (
    User,
    WearableSample,
    LabResult,
)

# -----------------------------
# CONFIG
# -----------------------------
USER_ID = 1       # the demo user ID
DAYS = 30         # how many days of data to generate
DEVICE = "fitbit" # wearable device type

# -----------------------------
# SEEDING FUNCTIONS
# -----------------------------

def seed_user(db):
    """Create a demo user if none exists."""
    repo = UserRepository(db)
    existing = repo.get_by_id(USER_ID)
    if existing:
        print(f"User {USER_ID} already exists — skipping")
        return existing

    user = repo.create(
        name="Demo User",
        email="demo@example.com",
        hashed_password="not_relevant_for_demo",
    )
    print("Created demo user.")
    return user

def seed_sleep_and_hrv(db, days=DAYS):
    """Generate synthetic trends for sleep, HRV, activity."""
    wearable_repo = WearableRepository(db)
    now = datetime.utcnow()

    print(f"Seeding {days} days of wearable data…")

    for i in range(days):
        ts = now - timedelta(days=i)

        # Sleep duration: slight upward trend
        wearable_repo.create(
            user_id=USER_ID,
            device_type=DEVICE,
            metric_type="sleep_duration",
            value=6.0 + (i * 0.05),
            unit="hours",
            timestamp=ts,
        )

        # HRV: slight downward trend
        wearable_repo.create(
            user_id=USER_ID,
            device_type=DEVICE,
            metric_type="hrv",
            value=70 - (i * 0.3),
            unit="ms",
            timestamp=ts,
        )

        # Activity minutes: upward trend
        wearable_repo.create(
            user_id=USER_ID,
            device_type=DEVICE,
            metric_type="activity_minutes",
            value=30 + (i * 2),
            unit="minutes",
            timestamp=ts,
        )

    print("Wearable data seeded.")

def seed_labs(db):
    """Seed a few fake metabolic labs to demonstrate lab-driven insights."""
    lab_repo = LabResultRepository(db)
    now = datetime.utcnow()

    print("Seeding lab results…")

    # Fasting glucose values
    for i, value in enumerate([5.4, 5.6, 5.9, 6.1]):
        lab_repo.create(
            user_id=USER_ID,
            test_name="fasting_glucose",
            value=value,
            unit="mmol/L",
            reference_range="3.8–5.5",
            timestamp=now - timedelta(days=(i * 7)),
        )

    # Vitamin D values
    for i, value in enumerate([68, 62, 55]):
        lab_repo.create(
            user_id=USER_ID,
            test_name="vitamin_d",
            value=value,
            unit="nmol/L",
            reference_range="50–125",
            timestamp=now - timedelta(days=(i * 30)),
        )

    print("Lab results seeded.")

def seed_symptoms(db):
    """Seed subjective symptom logs."""
    symptom_repo = SymptomRepository(db)
    now = datetime.utcnow()

    print("Seeding symptoms…")

    for i in range(10):
        symptom_repo.create(
            user_id=USER_ID,
            symptom_name="fatigue",
            severity="moderate",
            frequency="daily",
            notes="Feeling more tired than usual.",
            timestamp=now - timedelta(days=i),
        )

    print("Symptoms seeded.")

# -----------------------------
# MAIN
# -----------------------------

def main():
    db = SessionLocal()
    print("Starting database seeding…")
    seed_user(db)
    seed_sleep_and_hrv(db)
    seed_labs(db)
    seed_symptoms(db)
    db.close()
    print("Seeding complete. You can now test via API & Swagger.")

def seed_demo_data():
    """Alternative seeding function using direct model access."""
    db = SessionLocal()
    print("🌱 Seeding demo data...")
    
    # ---- User ----
    user = User(
        name="Demo User",
        email="demo@example.com",
        hashed_password="demo_hash",
        created_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # ---- Wearable data (sleep + HRV) ----
    for i in range(14):
        db.add(
            WearableSample(
                user_id=user.id,
                device_type="fitbit",
                metric_type="sleep_duration",
                value=6.5 + i * 0.1,
                unit="hours",
                timestamp=datetime.utcnow() - timedelta(days=i),
            )
        )
        db.add(
            WearableSample(
                user_id=user.id,
                device_type="fitbit",
                metric_type="hrv",
                value=75 - i,
                unit="ms",
                timestamp=datetime.utcnow() - timedelta(days=i),
            )
        )
    
    # ---- Lab result ----
    db.add(
        LabResult(
            user_id=user.id,
            test_name="vitamin_d",
            value=42,
            unit="ng/mL",
            reference_range="30-100",
            timestamp=datetime.utcnow(),
        )
    )
    
    db.commit()
    db.close()
    
    print("✅ Demo data seeded successfully.")


if __name__ == "__main__":
    # Run the repository-based seeding by default
    main()
    
    # Uncomment to use the direct model access version instead:
    # seed_demo_data()
