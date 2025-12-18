"""
Seed the database with synthetic demo data using the DemoProvider.

Usage (from backend/ directory):

    ENV_MODE=demo python scripts/seed_demo_data.py --user-id 1 --days 30 --scenario healthy_baseline
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.domain.models.user import User
from app.domain.repositories.health_data_repository import HealthDataRepository
from app.integrations.providers.demo import DemoProvider


def seed_demo_data(
    user_id: int,
    days: int = 30,
    scenario: str = "healthy_baseline",
) -> None:
    """Seed database with synthetic health data (idempotent per user/scenario window)."""

    db = SessionLocal()
    try:
        print(f"🌱 Seeding {days} days of '{scenario}' demo data for user {user_id}...")

        # Ensure user exists (minimal check).
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise RuntimeError(f"User {user_id} does not exist – create the user first.")

        provider = DemoProvider(scenario=scenario)

        end = datetime.utcnow()
        start = end - timedelta(days=days)

        # Generate synthetic points (no persistence yet).
        points = db_points = []
        # DemoProvider.fetch_data is async; run it via asyncio.run-style pattern.
        import asyncio

        async def _run() -> None:
            nonlocal points
            points = await provider.fetch_data(
                user_id=user_id,
                start=start,
                end=end,
                metrics=provider.get_supported_metrics(),
            )

        asyncio.run(_run())

        print(f"Generated {len(points)} synthetic points")

        # Persist via repository to keep a single ingestion path.
        repo = HealthDataRepository(db)
        for p in points:
            repo.create(
                user_id=p.user_id,
                data_type=p.metric_type,
                value=p.value,
                unit=p.unit,
                source=p.source,
                timestamp=p.timestamp,
            )

        print(f"✅ Seeded {len(points)} points for user {user_id}")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--scenario",
        default="healthy_baseline",
        choices=[
            "healthy_baseline",
            "sleep_debt_accumulation",
            "illness_episode",
            "stress_period",
            "intervention_response",
        ],
    )

    args = parser.parse_args()
    seed_demo_data(args.user_id, args.days, args.scenario)

