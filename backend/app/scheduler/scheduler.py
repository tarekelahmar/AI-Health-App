import os
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.scheduler.jobs import (
    job_run_insights_for_all_users,
    job_recompute_baselines_for_all_users,
    job_evaluate_due_experiments,
    job_generate_daily_inbox_items,
    job_dispatch_notifications,
    job_generate_daily_narratives,
    # SECURITY FIX: Removed broken job_sync_whoop_data import
    job_sync_whoop_for_all_users,
    job_generate_driver_findings,
    job_recompute_personal_drivers,
)

_scheduler: Optional[BackgroundScheduler] = None


def scheduler_enabled() -> bool:
    return os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"


def get_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is None:
        tz = os.getenv("SCHEDULER_TIMEZONE", "UTC")
        _scheduler = BackgroundScheduler(timezone=tz)
    return _scheduler


def configure_jobs(s: BackgroundScheduler) -> None:
    """
    Cron times are UTC by default unless SCHEDULER_TIMEZONE is set.
    """
    # Nightly: recompute baselines after ingestion / daily rollups
    s.add_job(
        job_recompute_baselines_for_all_users,
        CronTrigger(hour=2, minute=0),
        id="recompute_baselines",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Morning: generate insights loop (changes/trends/instability + guardrails)
    s.add_job(
        job_run_insights_for_all_users,
        CronTrigger(hour=6, minute=0),
        id="run_insights",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Midday: evaluate any active experiments that are due (if you use due logic)
    s.add_job(
        job_evaluate_due_experiments,
        CronTrigger(hour=12, minute=0),
        id="evaluate_experiments",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Evening: generate daily inbox items (reminders, summaries)
    s.add_job(
        job_generate_daily_inbox_items,
        CronTrigger(hour=19, minute=0),
        id="daily_inbox",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # NEW: dispatch outbox every 5 minutes
    s.add_job(
        job_dispatch_notifications,
        CronTrigger(minute="*/5"),
        id="dispatch_notifications",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Daily narrative generation (after insights run)
    s.add_job(
        job_generate_daily_narratives,
        CronTrigger(hour=7, minute=5),
        id="generate_daily_narratives",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # SECURITY FIX: Removed broken job_sync_whoop_data job registration
    # Use job_sync_whoop_for_all_users instead (uses ProviderSyncService correctly)

    # WHOOP sync for all users (daily at 01:30 UTC, before baselines at 02:00)
    s.add_job(
        job_sync_whoop_for_all_users,
        CronTrigger(hour=1, minute=30),
        id="sync_whoop_all",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Driver discovery (daily at 07:10 UTC, after narratives at 07:05)
    s.add_job(
        job_generate_driver_findings,
        CronTrigger(hour=7, minute=10),
        id="generate_driver_findings",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    # Personal drivers recomputation (daily at 07:15 UTC, after driver findings)
    s.add_job(
        job_recompute_personal_drivers,
        CronTrigger(hour=7, minute=15),
        id="recompute_personal_drivers",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )


def start_scheduler() -> None:
    if not scheduler_enabled():
        return
    s = get_scheduler()
    if not s.running:
        configure_jobs(s)
        s.start()


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
    _scheduler = None

