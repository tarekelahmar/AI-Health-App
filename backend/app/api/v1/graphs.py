import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.router_factory import make_v1_router
from app.api.auth_mode import get_request_user_id
from app.api.schemas.graphs import DriversResponse, SnapshotResponse, GraphDriverEdge
from app.domain.repositories.causal_graph_repository import CausalGraphRepository
from app.domain.repositories.experiment_repository import ExperimentRepository
from app.domain.repositories.health_data_repository import HealthDataRepository
from app.domain.repositories.adherence_repository import AdherenceRepository
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository

from app.engine.attribution.lagged_effects import LaggedEffectEngine
from app.engine.attribution.interaction_effects import InteractionAttributionEngine
from app.engine.graphs.driver_graph_builder import DriverGraphBuilder
from app.engine.guardrails import prune_driver_edges

# SECURITY: Changed from public_router to make_v1_router - graphs contain PHI
router = make_v1_router(prefix="/api/v1/graphs", tags=["graphs"])


@router.get("/drivers", response_model=DriversResponse)
def get_drivers(
    user_id: int = Depends(get_request_user_id),
    target_metric: str = Query(..., alias="target_metric"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    graph_repo = CausalGraphRepository(db)

    # return existing edges if already computed
    edges = graph_repo.list_top_drivers(user_id=user_id, target_metric_key=target_metric, limit=limit)
    items = []
    for e in edges:
        items.append(
            GraphDriverEdge(
                driver_key=e.driver_key,
                driver_kind=e.driver_kind,
                target_metric_key=e.target_metric_key,
                lag_days=e.lag_days,
                direction=e.direction,
                effect_size=e.effect_size,
                confidence=e.confidence,
                coverage=e.coverage,
                confounder_penalty=e.confounder_penalty,
                interaction_boost=e.interaction_boost,
                score=e.score,
                details=json.loads(e.details_json or "{}"),
            )
        )

    return DriversResponse(user_id=user_id, target_metric_key=target_metric, items=items)


@router.post("/compute", response_model=DriversResponse)
def compute_drivers(
    user_id: int = Depends(get_request_user_id),
    target_metric: str = Query(..., alias="target_metric"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    # repos
    exp_repo = ExperimentRepository(db)
    health_repo = HealthDataRepository(db)
    adh_repo = AdherenceRepository(db)
    checkin_repo = DailyCheckInRepository(db)
    graph_repo = CausalGraphRepository(db)

    # engines
    lag_engine = LaggedEffectEngine(
        health_repo=health_repo,
        experiment_repo=exp_repo,
        adherence_repo=adh_repo,
    )
    interaction_engine = InteractionAttributionEngine(
        health_repo=health_repo,
        experiment_repo=exp_repo,
    )
    builder = DriverGraphBuilder(
        lag_engine=lag_engine,
        interaction_engine=interaction_engine,
        checkin_repo=checkin_repo,
    )

    out = builder.build_for_target(
        user_id=user_id,
        target_metric_key=target_metric,
        experiment_repo=exp_repo,
        health_repo=health_repo,
        adherence_repo=adh_repo,
        limit=limit,
    )

    # Apply driver graph guardrails: prune unsafe or weak edges
    pruned_edges = prune_driver_edges(out["edges"])
    out["edges"] = pruned_edges
    out["snapshot"]["edges"] = pruned_edges

    graph_repo.upsert_edges(pruned_edges)
    graph_repo.save_snapshot(user_id, out["snapshot"])

    # Return as DriversResponse (already pruned above)
    items = [
        GraphDriverEdge(
            driver_key=e["driver_key"],
            driver_kind=e["driver_kind"],
            target_metric_key=e["target_metric_key"],
            lag_days=e["lag_days"],
            direction=e["direction"],
            effect_size=e["effect_size"],
            confidence=e["confidence"],
            coverage=e["coverage"],
            confounder_penalty=e["confounder_penalty"],
            interaction_boost=e["interaction_boost"],
            score=e["score"],
            details=e.get("details", {}),
        )
        for e in pruned_edges
    ]
    return DriversResponse(user_id=user_id, target_metric_key=target_metric, items=items)


@router.get("/snapshot", response_model=SnapshotResponse)
def get_snapshot(
    user_id: int = Depends(get_request_user_id),
    db: Session = Depends(get_db),
):
    graph_repo = CausalGraphRepository(db)
    snap = graph_repo.get_latest_snapshot(user_id=user_id)
    if not snap:
        return SnapshotResponse(user_id=user_id, snapshot={"note": "No snapshot yet. Call POST /graphs/compute first."})
    return SnapshotResponse(user_id=user_id, snapshot=json.loads(snap.snapshot_json or "{}"))

