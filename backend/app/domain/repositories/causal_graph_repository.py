import json
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.domain.models.causal_graph_edge import CausalGraphEdge
from app.domain.models.causal_graph_snapshot import CausalGraphSnapshot


class CausalGraphRepository:
    def __init__(self, db: Session):
        self.db = db

    def upsert_edges(self, edges: List[dict]) -> int:
        """
        Simple MVP: delete existing edges for (user_id, target_metric_key) then insert new.
        """
        if not edges:
            return 0

        user_id = edges[0]["user_id"]
        target = edges[0]["target_metric_key"]

        self.db.query(CausalGraphEdge).filter(
            CausalGraphEdge.user_id == user_id,
            CausalGraphEdge.target_metric_key == target,
        ).delete()

        for e in edges:
            self.db.add(
                CausalGraphEdge(
                    user_id=e["user_id"],
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
                    details_json=json.dumps(e.get("details", {})),
                )
            )

        self.db.commit()
        return len(edges)

    def list_top_drivers(self, user_id: int, target_metric_key: str, limit: int = 10) -> List[CausalGraphEdge]:
        return (
            self.db.query(CausalGraphEdge)
            .filter(
                CausalGraphEdge.user_id == user_id,
                CausalGraphEdge.target_metric_key == target_metric_key,
            )
            .order_by(desc(CausalGraphEdge.score))
            .limit(limit)
            .all()
        )

    def save_snapshot(self, user_id: int, snapshot: dict) -> CausalGraphSnapshot:
        snap = CausalGraphSnapshot(user_id=user_id, snapshot_json=json.dumps(snapshot))
        self.db.add(snap)
        self.db.commit()
        self.db.refresh(snap)
        return snap

    def get_latest_snapshot(self, user_id: int) -> Optional[CausalGraphSnapshot]:
        return (
            self.db.query(CausalGraphSnapshot)
            .filter(CausalGraphSnapshot.user_id == user_id)
            .order_by(desc(CausalGraphSnapshot.generated_at))
            .first()
        )

