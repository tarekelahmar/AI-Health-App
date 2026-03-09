import json
from typing import Dict, List, Any, Optional, Tuple
from math import copysign
from datetime import date, timedelta, datetime

from app.domain.metrics.registry import METRIC_REGISTRY as METRICS
from app.engine.attribution.lagged_effects import LaggedEffectEngine
from app.engine.attribution.interaction_effects import InteractionAttributionEngine
from app.domain.repositories.daily_checkin_repository import DailyCheckInRepository


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _direction_from_effect(effect_size: float) -> str:
    return "up" if effect_size > 0 else "down"


def _score(effect_size: float, confidence: float, coverage: float, confounder_penalty: float, interaction_boost: float) -> float:
    """
    Simple, transparent ranking score:
      base = |effect| * confidence * coverage
      + interaction_boost
      - confounder_penalty
    """
    base = abs(effect_size) * confidence * coverage
    return round(base + interaction_boost - confounder_penalty, 6)


class DriverGraphBuilder:
    """
    Produces ranked driver edges for a given target metric.
    Inputs:
      - lagged attribution results (Step H)
      - interaction results (Step I)
      - check-in behaviors as confounders
    """

    def __init__(
        self,
        *,
        lag_engine: LaggedEffectEngine,
        interaction_engine: InteractionAttributionEngine,
        checkin_repo: DailyCheckInRepository,
    ):
        self.lag_engine = lag_engine
        self.interaction_engine = interaction_engine
        self.checkin_repo = checkin_repo

    def build_for_target(
        self,
        *,
        user_id: int,
        target_metric_key: str,
        experiment_repo,
        health_repo,
        adherence_repo,
        window_days: int = 21,
        confounders: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Returns dict with:
          edges: list[edge_dict]
          snapshot: graph JSON
        """

        confounders = confounders or ["caffeine_pm", "alcohol", "late_meal"]

        # 1) Get due/active experiments as "intervention drivers"
        experiments = experiment_repo.list_by_user(user_id=user_id)
        active_or_recent = [e for e in experiments if e.status in ("active", "stopped")]

        edges: List[Dict[str, Any]] = []

        # Pull check-ins in range (for interactions/confounders)
        # Use a wide date range to get all check-ins
        today = date.today()
        start_date_range = today - timedelta(days=90)
        checkins = self.checkin_repo.list_range(user_id=user_id, start_date=start_date_range, end_date=today, limit=90)

        # 2) Build lagged effects for each experiment on the target metric
        base_attributions = []
        for exp in active_or_recent:
            # Use existing run() method
            attrs = self.lag_engine.run(
                experiment_id=exp.id,
                metric_key=target_metric_key,
                baseline_days=14,
            )
            base_attributions.extend(attrs)

        # Keep only strongest lag per intervention_id
        by_intervention = {}
        for a in base_attributions:
            key = (a.intervention_id, a.metric_key)
            if key not in by_intervention or abs(a.effect_size) > abs(by_intervention[key].effect_size):
                by_intervention[key] = a

        pruned = list(by_intervention.values())

        # 3) Interaction effects (MVP: test 1 confounder at a time; expand later)
        interaction_results = []
        for exp in active_or_recent:
            for c in confounders:
                try:
                    interaction_results.extend(
                        self.interaction_engine.run(
                            base_attributions=[a for a in pruned if a.intervention_id == exp.intervention_id],
                            daily_checkins=checkins,
                            confounder_key=c,
                            experiment_id=exp.id,
                        )
                    )
                except Exception:
                    # keep graph resilient in MVP
                    continue

        # Build lookup: (intervention_id, metric_key, confounder) -> delta
        interaction_lookup = {}
        for ir in interaction_results:
            interaction_lookup[(ir.intervention_id, ir.metric_key, ir.confounder_key)] = float(ir.delta_vs_control)

        # 4) Confounder penalty heuristic:
        # if confounder is frequently present, penalize attribution certainty (observational noise).
        conf_penalty = {}
        if checkins:
            total = len(checkins)
            for c in confounders:
                present = sum(1 for x in checkins if x.behaviors_json.get(c) is True)
                rate = present / total if total else 0.0
                conf_penalty[c] = round(rate * 0.2, 3)  # max 0.2 penalty

        # 5) Create edges for interventions
        for a in pruned:
            # Interaction boost: if any confounder delta suggests "works better when confounder absent"
            # delta_vs_control < 0 means confounder presence reduces effect (we reward driver stability by +boost when avoid confounder)
            interaction_boost = 0.0
            interaction_notes = []

            for c in confounders:
                delta = interaction_lookup.get((a.intervention_id, a.metric_key, c))
                if delta is None:
                    continue
                # If delta is negative, intervention seems worse under confounder presence; reward clarity by boosting but also attach notes
                if delta < -0.4:
                    interaction_boost += 0.08
                    interaction_notes.append(f"Effect reduced when {c} present (Δ={delta:.2f}).")

            # Confounder penalty: if confounders are common overall, reduce score slightly
            confounder_penalty = sum(conf_penalty.values()) if conf_penalty else 0.0

            score = _score(a.effect_size, a.confidence, a.coverage, confounder_penalty, interaction_boost)

            edges.append(
                {
                    "user_id": user_id,
                    "driver_key": str(a.intervention_id),
                    "driver_kind": "intervention",
                    "target_metric_key": target_metric_key,
                    "lag_days": int(a.lag_days),
                    "direction": _direction_from_effect(a.effect_size),
                    "effect_size": round(float(a.effect_size), 6),
                    "confidence": _clamp01(float(a.confidence)),
                    "coverage": _clamp01(float(a.coverage)),
                    "confounder_penalty": round(confounder_penalty, 6),
                    "interaction_boost": round(interaction_boost, 6),
                    "score": score,
                    "details": {
                        "interaction_notes": interaction_notes,
                        "raw": a.details or {},
                    },
                }
            )

        # 6) OPTIONAL: metric-to-metric drivers (MVP)
        # For now we keep it minimal: include a few behavioral metrics as "behavior" drivers if they exist in METRICS registry.
        for c in confounders:
            # represent as behavior driver edge with low confidence until we explicitly model it
            edges.append(
                {
                    "user_id": user_id,
                    "driver_key": c,
                    "driver_kind": "behavior",
                    "target_metric_key": target_metric_key,
                    "lag_days": 0,
                    "direction": "down",
                    "effect_size": 0.0,
                    "confidence": 0.2,
                    "coverage": 0.5,
                    "confounder_penalty": 0.0,
                    "interaction_boost": 0.0,
                    "score": 0.0,
                    "details": {
                        "note": "Behavior driver placeholder — will be upgraded when we add explicit behavior→metric modeling."
                    },
                }
            )

        # Rank and clip
        edges_sorted = sorted(edges, key=lambda e: e["score"], reverse=True)
        top_edges = edges_sorted[:limit]

        snapshot = {
            "user_id": user_id,
            "target_metric_key": target_metric_key,
            "generated_from": ["lagged_effects", "interaction_effects", "confounder_penalty"],
            "edges": top_edges,
        }

        return {"edges": top_edges, "snapshot": snapshot}

