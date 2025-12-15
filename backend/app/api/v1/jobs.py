from fastapi import APIRouter
from app.api.schemas.jobs import JobsListOut, JobOut
from app.scheduler.scheduler import scheduler_enabled, get_scheduler

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.get("", response_model=JobsListOut)
def list_jobs():
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

