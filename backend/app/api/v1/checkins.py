import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, Query

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.api.schemas.checkins import DailyCheckInCreate, DailyCheckInUpdate, DailyCheckInResponse

from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository
from app.api.auth_mode import get_request_user_id
from app.api.router_factory import make_v1_router
from app.engine.checkin_bridge import sync_checkin_to_datapoints

logger = logging.getLogger(__name__)

router = make_v1_router(prefix="/api/v1/checkins", tags=["checkins"])


def _run_journal_patterns(user_id: int):
    """Background task: compute journal patterns after check-in save."""
    try:
        from app.core.database import SessionLocal
        from app.engine.journal_pattern_engine import compute_journal_patterns
        db = SessionLocal()
        try:
            result = compute_journal_patterns(db, user_id)
            logger.info(
                f"Journal patterns computed: {result.patterns_found} found, "
                f"{result.patterns_new} new, {result.patterns_updated} updated"
            )
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Journal pattern computation failed: {e}")


@router.post("/upsert", response_model=DailyCheckInResponse)
def upsert_checkin(
    payload: DailyCheckInCreate,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    # Override payload.user_id with authenticated user_id (prevent spoofing)
    payload.user_id = user_id

    # Compute word count from notes
    word_count = len(payload.notes.split()) if payload.notes and payload.notes.strip() else None

    repo = DailyCheckInRepository(db)
    obj = repo.upsert_for_date(
        user_id=payload.user_id,
        checkin_date=payload.checkin_date,
        # V2 slider fields
        overall_wellbeing=payload.overall_wellbeing,
        energy=payload.energy,
        mood=payload.mood,
        focus=payload.focus,
        connection=payload.connection,
        # V1 deprecated fields (still accepted)
        sleep_quality=payload.sleep_quality,
        stress=payload.stress,
        # Text & behaviors
        notes=payload.notes,
        behaviors_json=payload.behaviors_json,
        # Metadata
        word_count=word_count,
    )
    # Bridge: sync subjective data into HealthDataPoint for the insight pipeline
    sync_checkin_to_datapoints(db, obj)

    # Trigger journal pattern computation if behaviors_json has content
    if payload.behaviors_json and any(
        isinstance(v, bool) or v in (0, 1) for v in payload.behaviors_json.values()
    ):
        background_tasks.add_task(_run_journal_patterns, user_id)

    return obj


@router.patch("/{checkin_date}", response_model=DailyCheckInResponse)
def update_checkin(
    checkin_date: date,
    payload: DailyCheckInUpdate,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    repo = DailyCheckInRepository(db)
    obj = repo.upsert_for_date(
        user_id=user_id,
        checkin_date=checkin_date,
        # V2 fields
        overall_wellbeing=payload.overall_wellbeing,
        energy=payload.energy,
        mood=payload.mood,
        focus=payload.focus,
        connection=payload.connection,
        # V1 deprecated
        sleep_quality=payload.sleep_quality,
        stress=payload.stress,
        # Text & behaviors
        notes=payload.notes,
        behaviors_json=payload.behaviors_json if payload.behaviors_json is not None else None,
        adherence_rate=payload.adherence_rate,
    )
    # Bridge: sync subjective data into HealthDataPoint for the insight pipeline
    sync_checkin_to_datapoints(db, obj)
    return obj


@router.get("/{checkin_date}", response_model=DailyCheckInResponse)
def get_checkin(
    checkin_date: date,
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db)
):
    repo = DailyCheckInRepository(db)
    obj = repo.get_by_date(user_id=user_id, checkin_date=checkin_date)
    if not obj:
        # Return an "empty" checkin shape via upsert with no fields.
        # TODO(Phase 4): This auto-creates a DB row on GET, which will
        # inflate "consecutive entry days" for milestone detection. When
        # implementing milestones, distinguish real entries (word_count > 0
        # or any slider non-null) from placeholder rows created here.
        obj = repo.upsert_for_date(user_id=user_id, checkin_date=checkin_date, behaviors_json={})
    return obj


@router.get("", response_model=list[DailyCheckInResponse])
def list_checkins(
    user_id: int = Depends(get_request_user_id),
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db),
):
    repo = DailyCheckInRepository(db)
    return repo.list_range(user_id=user_id, start_date=start_date, end_date=end_date, limit=limit)
