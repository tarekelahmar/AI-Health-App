from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db

router = APIRouter(prefix="/api/v1/health", tags=["ops"], dependencies=[])

@router.get("/live")
def live():
    return {"ok": True}

@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    # Minimal readiness: DB connection
    from sqlalchemy import text
    db.execute(text("SELECT 1"))
    return {"ok": True, "db": "ok"}

