from fastapi import APIRouter
from app.engine.coverage_matrix import generate_coverage_matrix
from app.api.public_router import public_router

router = public_router(prefix="", tags=["coverage"])


@router.get("/metrics")
def get_metric_coverage():
    return generate_coverage_matrix()

