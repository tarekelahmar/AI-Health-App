"""Minimal job scheduler for MVP / dev

STEP L: You need *some* orchestration to run daily loop automatically.
For production, replace with:
- Celery + Redis, or
- AWS EventBridge + ECS task, or
- APScheduler inside a worker container (acceptable for MVP).
"""

import os
import logging
from typing import Optional
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.database import SessionLocal
from app.engine.loop_runner import run_loop

log = logging.getLogger(__name__)

def _run_daily_loop_for_user_ids(user_ids: list[int]) -> None:
    db = SessionLocal()
    try:
        for uid in user_ids:
            try:
                run_loop(user_id=uid, db=db)
                log.info("daily_loop_ok user_id=%s", uid)
            except Exception:
                log.exception("daily_loop_failed user_id=%s", uid)
    finally:
        db.close()

from typing import Optional

def start_scheduler() -> Optional[BackgroundScheduler]:
    """Start scheduler if enabled.

Env:
  ENABLE_SCHEDULER=true
  SCHEDULER_USER_IDS=1,2,3
  SCHEDULER_CRON_HOUR=7  (UTC)
"""
    if os.getenv("ENABLE_SCHEDULER", "false").lower() != "true":
        return None

    raw_ids = os.getenv("SCHEDULER_USER_IDS", "1")
    user_ids = [int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()]
    hour = int(os.getenv("SCHEDULER_CRON_HOUR", "7"))

    sched = BackgroundScheduler(timezone=timezone.utc)
    # run daily at HH:00 UTC
    sched.add_job(
        _run_daily_loop_for_user_ids,
        "cron",
        hour=hour,
        minute=0,
        args=[user_ids],
        id="daily_loop",
        replace_existing=True,
    )
    sched.start()
    log.info("scheduler_started hour=%s user_ids=%s", hour, user_ids)
    return sched

