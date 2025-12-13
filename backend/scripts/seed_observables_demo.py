import random
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.api.schemas.health_data import HealthDataBatchIn, HealthDataPointIn
from app.api.v1.health_data import ingest_health_data_batch


def seed_observables(user_id: int = 1, days: int = 21):
    db = SessionLocal()
    now = datetime.utcnow()

    points = []
    for d in range(days):
        day = now - timedelta(days=days - d)

        # sleep_duration (minutes)
        sleep_minutes = random.randint(330, 510)  # 5.5h to 8.5h
        # sleep_efficiency (%)
        sleep_eff = random.uniform(75, 95)
        # resting_hr
        rhr = random.uniform(52, 78)
        # hrv_rmssd
        hrv = random.uniform(25, 70)
        # steps
        steps = random.randint(2000, 12000)

        # subjective check-in (scores 1-5)
        sleep_q = random.choice([2, 3, 3, 4, 4, 5])
        energy = random.choice([2, 3, 3, 4, 5])
        stress = random.choice([2, 2, 3, 3, 4, 5])

        points.extend([
            HealthDataPointIn(metric_key="sleep_duration", value=float(sleep_minutes), timestamp=day, source="wearable"),
            HealthDataPointIn(metric_key="sleep_efficiency", value=float(sleep_eff), timestamp=day, source="wearable"),
            HealthDataPointIn(metric_key="resting_hr", value=float(rhr), timestamp=day, source="wearable"),
            HealthDataPointIn(metric_key="hrv_rmssd", value=float(hrv), timestamp=day, source="wearable"),
            HealthDataPointIn(metric_key="steps", value=float(steps), timestamp=day, source="wearable"),
            HealthDataPointIn(metric_key="sleep_quality", value=float(sleep_q), timestamp=day, source="manual"),
            HealthDataPointIn(metric_key="energy", value=float(energy), timestamp=day, source="manual"),
            HealthDataPointIn(metric_key="stress", value=float(stress), timestamp=day, source="manual"),
        ])

    payload = HealthDataBatchIn(user_id=user_id, points=points)
    out = ingest_health_data_batch(payload, db=db)
    print(out)
    db.close()


if __name__ == "__main__":
    seed_observables(user_id=1, days=21)

