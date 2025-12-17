from fastapi import APIRouter, Depends
from app.api.schemas.jobs import JobsListOut, JobOut
from app.scheduler.scheduler import scheduler_enabled, get_scheduler
from app.api.router_factory import make_v1_router
from app.api.auth_mode import get_request_user_id

# AUDIT FIX: Use make_v1_router and require auth
router = make_v1_router(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("", response_model=JobsListOut)
def list_jobs(
    user_id: int = Depends(get_request_user_id),
):
    """
    List scheduled jobs.
    
    AUDIT FIX: Requires authentication to prevent operational reconnaissance.
    """
    enabled = scheduler_enabled()
    s = get_scheduler()
    jobs = []
    for j in s.get_jobs():
        jobs.append(JobOut(
            id=j.id,
            name=j.name,
            next_run_time=j.next_run_time.isoformat() if j.next_run_time else None,
            trigger=str(j.trigger),
        ))
    return JobsListOut(enabled=enabled, running=s.running, jobs=jobs)

