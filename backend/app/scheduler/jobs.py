"""
Background jobs run in-process (APScheduler BackgroundScheduler).
Each job opens its own DB session, does work, and closes safely.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from app.core.database import SessionLocal

# Repos / services you already have
from app.domain.repositories.user_repository import UserRepository
from app.domain.repositories.experiment_repository import ExperimentRepository
from app.domain.repositories.evaluation_repository import EvaluationRepository
from app.domain.repositories.loop_decision_repository import LoopDecisionRepository
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository

from app.engine.loop_runner import run_loop  # your multi-metric loop runner
from app.engine.baseline_service import recompute_baseline  # baseline compute per user+metric
from app.domain.metric_registry import METRICS
from app.domain.repositories.notification_outbox_repository import NotificationOutboxRepository
from app.engine.notifications.dispatchers import DISPATCHERS
from app.engine.synthesis.narrative_synthesizer import generate_and_persist_narrative
from app.engine.notifications.notification_service import NotificationService
from app.engine.providers.provider_sync_service import ProviderSyncService
from datetime import date

# We add Inbox/Notifications in STEP M, but jobs can import lazily to avoid hard dependency

def _now_utc() -> datetime:
    return datetime.utcnow()


def _today() -> date:
    return _now_utc().date()


def _list_all_user_ids(db) -> List[int]:
    # UserRepository uses list_users method
    try:
        users = UserRepository(db).list_users(limit=10_000, offset=0)
    except AttributeError:
        # Fallback: query directly
        from app.domain.models.user import User
        users = db.query(User).limit(10_000).all()
    return [u.id for u in users]


def job_run_insights_for_all_users() -> None:
    db = SessionLocal()
    try:
        user_ids = _list_all_user_ids(db)
        for uid in user_ids:
            try:
                run_loop(db=db, user_id=uid)
            except Exception as e:
                # keep scheduler alive; log minimally
                print(f"[job_run_insights] user_id={uid} error={e}")
    finally:
        db.close()


def job_recompute_baselines_for_all_users(window_days: int = 21) -> None:
    db = SessionLocal()
    try:
        user_ids = _list_all_user_ids(db)
        metric_keys = list(METRICS.keys())
        for uid in user_ids:
            for mk in metric_keys:
                try:
                    recompute_baseline(db=db, user_id=uid, metric_key=mk, window_days=window_days)
                except Exception as e:
                    print(f"[job_recompute_baselines] user_id={uid} metric={mk} error={e}")
    finally:
        db.close()


def job_evaluate_due_experiments() -> None:
    """
    Minimal: evaluate ACTIVE experiments that ended OR are older than N days.
    If your ExperimentRepository already has 'list_active' or 'list_due', use that.
    """
    db = SessionLocal()
    try:
        exp_repo = ExperimentRepository(db)
        eval_repo = EvaluationRepository(db)
        decision_repo = LoopDecisionRepository(db)

        # Try to use a 'list' API (MVP)
        # Get all experiments by querying for each user (MVP approach)
        user_repo = UserRepository(db)
        users = user_repo.list(limit=1000, offset=0)
        experiments = []
        for user in users:
            user_exps = exp_repo.list_by_user(user_id=user.id, limit=100)
            experiments.extend(user_exps)

        for exp in experiments:
            if getattr(exp, "status", None) != "active":
                continue

            started_at = getattr(exp, "started_at", None)
            ended_at = getattr(exp, "ended_at", None)
            if started_at is None:
                continue

            # Due if ended, or older than 14 days
            due = ended_at is not None or (_now_utc() - started_at) >= timedelta(days=14)
            if not due:
                continue

            try:
                # Your API endpoint does evaluation; here we call repository/service-level logic
                # If you have a service function, prefer it. Otherwise, let UI call /evaluate.
                # We'll just mark "due" via inbox in STEP M.
                pass
            except Exception as e:
                print(f"[job_evaluate_due_experiments] exp_id={exp.id} error={e}")

    finally:
        db.close()


def job_generate_daily_inbox_items() -> None:
    """
    Creates: daily check-in reminder if missing.
    (Insight summaries + experiment reminders are added in STEP M once Inbox exists.)
    """
    db = SessionLocal()
    try:
        user_ids = _list_all_user_ids(db)
        checkin_repo = DailyCheckInRepository(db)

        for uid in user_ids:
            try:
                today = _today()
                existing = checkin_repo.get_by_date(user_id=uid, checkin_date=today)
                if existing is None:
                    # Use NotificationService for idempotent notification creation
                    try:
                        from app.engine.notifications.notification_service import NotificationService
                        notif = NotificationService(db)
                        notif.daily_checkin_reminder(user_id=uid, checkin_date=today)
                        db.commit()
                    except Exception as e:
                        # Inbox not installed yet or other error
                        print(f"[job_daily_inbox] user_id={uid} inbox_error={e}")
            except Exception as e:
                print(f"[job_daily_inbox] user_id={uid} error={e}")
    finally:
        db.close()


def job_dispatch_notifications(limit: int = 200) -> None:
    """
    Runs frequently. Pulls pending rows from outbox and dispatches them.
    Safe to run repeatedly. Uses attempt_count + last_error for debugging.
    """
    db: Session = SessionLocal()
    try:
        repo = NotificationOutboxRepository(db)
        pending = repo.list_pending(limit=limit)

        for row in pending:
            try:
                dispatcher = DISPATCHERS.get(row.channel)
                if not dispatcher:
                    raise ValueError(f"Unknown channel: {row.channel}")
                dispatcher(row.payload_json or "{}")
                repo.mark_dispatched(row.id)
                db.commit()
            except Exception as e:
                repo.mark_failed(row.id, str(e))
                db.commit()
    finally:
        db.close()


def job_generate_daily_narratives() -> None:
    """
    Generates today's daily narrative for all users.
    Also enqueues an inbox+outbox notification (idempotent via NotificationService dedupe).
    """
    db: Session = SessionLocal()
    try:
        user_repo = UserRepository(db)
        users = user_repo.list_users(limit=1000, offset=0)
        today = _today()

        notif = NotificationService(db)

        for u in users:
            try:
                narrative = generate_and_persist_narrative(
                    db,
                    user_id=u.id,
                    period_type="daily",
                    start=today,
                    end=today,
                    include_llm_translation=False,
                )
                # Create a user-visible inbox notification (idempotent)
                dedupe_key = f"daily_narrative:{u.id}:{today.isoformat()}"
                notif.create_inbox_only(
                    user_id=u.id,
                    category="insight",
                    title="Your daily summary is ready",
                    body=narrative.summary,
                    metadata={"narrative_id": narrative.id, "period_type": "daily", "date": today.isoformat()},
                    dedupe_key=dedupe_key,
                )
                db.commit()
            except Exception as e:
                print(f"[job_generate_daily_narratives] user_id={u.id} error={e}")
    finally:
        db.close()


def job_sync_whoop_data() -> None:
    """
    Sync WHOOP data for all users with connected accounts.
    Runs every 6 hours (WHOOP data latency friendly).
    """
    db: Session = SessionLocal()
    try:
        from app.providers.whoop.adapter import WhoopAdapter
        from app.domain.repositories.provider_token_repository import ProviderTokenRepository
        from app.engine.ingestion.provider_ingestion_service import ProviderIngestionService
        from app.domain.models.provider_token import ProviderToken
        from datetime import datetime, timedelta
        
        adapter = WhoopAdapter()
        token_repo = ProviderTokenRepository(db)
        ingestion_service = ProviderIngestionService(db)
        
        # Get all WHOOP tokens
        tokens = (
            db.query(ProviderToken)
            .filter(ProviderToken.provider_key == "whoop")
            .all()
        )
        
        for token in tokens:
            try:
                # Check if token needs refresh
                if token.expires_at and token.expires_at < datetime.utcnow():
                    if not token.refresh_token:
                        # Token expired, disable provider
                        token_repo.delete_tokens(token.user_id, "whoop")
                        print(f"[job_sync_whoop_data] Token expired for user_id={token.user_id}, removed")
                        continue
                    
                    # Refresh token
                    access_token = adapter.refresh_token(token.refresh_token)
                    token_repo.upsert_tokens(token.user_id, "whoop", access_token)
                    access_token_str = access_token.access_token
                else:
                    access_token_str = token.access_token
                
                # Fetch last 48h data
                raw_data = adapter.fetch_raw_data(
                    access_token_str,
                    since=datetime.utcnow() - timedelta(hours=48),
                )
                
                # Normalize
                normalized = adapter.normalize(raw_data)
                
                # Ingest
                result = ingestion_service.ingest_provider_data(
                    user_id=token.user_id,
                    provider_key="whoop",
                    normalized_points=normalized,
                )
                
                print(f"[job_sync_whoop_data] user_id={token.user_id} inserted={result['inserted']} rejected={result['rejected']}")
                
            except Exception as e:
                print(f"[job_sync_whoop_data] user_id={token.user_id} error={e}")
                # Continue with other users
    finally:
        db.close()


def job_sync_whoop_for_all_users() -> None:
    """
    MVP: sync WHOOP for all users who have a token.
    NOTE: you likely have a Users repository; if not, query users table directly.
    """
    db: Session = SessionLocal()
    try:
        # Lazy import to avoid circular deps
        from app.domain.models.user import User
        from app.domain.repositories.provider_token_repository import ProviderTokenRepository

        token_repo = ProviderTokenRepository(db)
        svc = ProviderSyncService(db)

        users = db.query(User).all()
        since = datetime.utcnow() - timedelta(days=7)  # keep it light; daily jobs can be 7d
        for u in users:
            tok = token_repo.get(user_id=u.id, provider="whoop")
            if not tok:
                continue
            try:
                svc.sync_whoop(user_id=u.id, since=since)
            except Exception:
                # swallow per-user failures so job continues
                continue
    finally:
        db.close()


def job_generate_driver_findings() -> None:
    """
    Generate driver findings for all users.
    Runs at 07:10 UTC (after narratives at 07:05).
    Creates InboxItem "New drivers found" if high-confidence findings exist.
    """
    db: Session = SessionLocal()
    try:
        from app.domain.models.user import User
        from app.engine.drivers.driver_discovery_service import DriverDiscoveryService
        from app.engine.notifications.notification_service import NotificationService
        
        user_repo = UserRepository(db)
        users = user_repo.list_users()
        notif = NotificationService(db)
        
        for u in users:
            try:
                service = DriverDiscoveryService(db)
                findings = service.discover_drivers(
                    user_id=u.id,
                    window_days=28,
                    max_findings=50,
                )
                
                # Filter high-confidence findings (>= 0.7)
                high_confidence = [f for f in findings if f.confidence >= 0.7]
                
                if high_confidence:
                    # Create inbox notification
                    notif.create_inbox_only(
                        user_id=u.id,
                        category="insight",
                        dedupe_key=f"driver_findings_{date.today().isoformat()}",
                        title="New driver associations found",
                        body=f"{len(high_confidence)} high-confidence associations detected between your behaviors/interventions and metrics.",
                        metadata={
                            "findings_count": len(high_confidence),
                            "top_findings": [
                                {
                                    "exposure_key": f.exposure_key,
                                    "metric_key": f.metric_key,
                                    "direction": f.direction,
                                    "confidence": f.confidence,
                                }
                                for f in high_confidence[:5]
                            ],
                        },
                    )
                    db.commit()
                    print(f"[job_generate_driver_findings] user_id={u.id} found {len(high_confidence)} high-confidence findings")
            except Exception as e:
                print(f"[job_generate_driver_findings] user_id={u.id} error={e}")
    finally:
        db.close()


def job_recompute_personal_drivers() -> None:
    """
    Recompute personal drivers for all users.
    Runs nightly after insights + evaluations.
    Only runs if sufficient new data exists.
    """
    db: Session = SessionLocal()
    try:
        user_repo = UserRepository(db)
        users = user_repo.list_users()
        
        from app.engine.attribution.cross_signal_engine import CrossSignalAttributionEngine
        
        for u in users:
            try:
                engine = CrossSignalAttributionEngine(db)
                drivers = engine.compute_personal_drivers(
                    user_id=u.id,
                    window_days=28,
                )
                print(f"[job_recompute_personal_drivers] user_id={u.id} computed {len(drivers)} drivers")
            except Exception as e:
                print(f"[job_recompute_personal_drivers] user_id={u.id} error={e}")
    finally:
        db.close()

