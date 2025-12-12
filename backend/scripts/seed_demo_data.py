from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.domain.models import User, WearableSample, LabResult

def seed_demo_data():
    db = SessionLocal()

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
    seed_demo_data()