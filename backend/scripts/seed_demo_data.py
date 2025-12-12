"""Idempotent demo data seeder

This script can be run multiple times without creating duplicates.
It uses upsert patterns to ensure data consistency.
"""
from datetime import datetime, timedelta
from sqlalchemy import func

from app.core.database import SessionLocal
from app.domain.models import User, WearableSample, LabResult


def seed_demo_data():
    """Seed demo data - idempotent (safe to run multiple times)"""
    db = SessionLocal()

    try:
        print("🌱 Seeding demo data...")

        # ---- User ----
        # Check if user already exists
        user = db.query(User).filter(User.email == "demo@example.com").first()
        if user:
            print(f"✅ User already exists (ID: {user.id}), using existing user...")
        else:
            user = User(
                name="Demo User",
                email="demo@example.com",
                hashed_password="demo_hash",
                created_at=datetime.utcnow(),
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✅ Created new user (ID: {user.id})")

        # ---- Wearable data (sleep + HRV) ----
        # Use upsert pattern: check if sample exists before adding
        wearable_samples_created = 0
        wearable_samples_existing = 0
        
        for i in range(14):
            target_date = datetime.utcnow() - timedelta(days=i)
            
            # Sleep duration sample
            sleep_sample = db.query(WearableSample).filter(
                WearableSample.user_id == user.id,
                WearableSample.device_type == "fitbit",
                WearableSample.metric_type == "sleep_duration",
                WearableSample.timestamp >= target_date - timedelta(hours=12),
                WearableSample.timestamp <= target_date + timedelta(hours=12),
            ).first()
            
            if not sleep_sample:
                db.add(
                    WearableSample(
                        user_id=user.id,
                        device_type="fitbit",
                        metric_type="sleep_duration",
                        value=6.5 + i * 0.1,
                        unit="hours",
                        timestamp=target_date,
                    )
                )
                wearable_samples_created += 1
            else:
                wearable_samples_existing += 1
            
            # HRV sample
            hrv_sample = db.query(WearableSample).filter(
                WearableSample.user_id == user.id,
                WearableSample.device_type == "fitbit",
                WearableSample.metric_type == "hrv",
                WearableSample.timestamp >= target_date - timedelta(hours=12),
                WearableSample.timestamp <= target_date + timedelta(hours=12),
            ).first()
            
            if not hrv_sample:
                db.add(
                    WearableSample(
                        user_id=user.id,
                        device_type="fitbit",
                        metric_type="hrv",
                        value=75 - i,
                        unit="ms",
                        timestamp=target_date,
                    )
                )
                wearable_samples_created += 1
            else:
                wearable_samples_existing += 1

        if wearable_samples_created > 0:
            print(f"✅ Created {wearable_samples_created} new wearable samples")
        if wearable_samples_existing > 0:
            print(f"ℹ️  Skipped {wearable_samples_existing} existing wearable samples")

        # ---- Lab result ----
        # Check if this specific lab result already exists (same test, same day)
        today = datetime.utcnow().date()
        lab_result = db.query(LabResult).filter(
            LabResult.user_id == user.id,
            LabResult.test_name == "vitamin_d",
            func.date(LabResult.timestamp) == today,
        ).first()
        
        if not lab_result:
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
            print("✅ Created new lab result")
        else:
            print(f"ℹ️  Lab result for vitamin_d already exists for today, skipping...")

        db.commit()
        print("✅ Demo data seeded successfully (idempotent - safe to rerun).")

    except Exception as e:
        db.rollback()
        print(f"❌ Error seeding data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
