"""
Cascade Detector - Phase 4.1

Detects and explains cascading effects across health domains.

When a change is detected in one domain (e.g., sleep disruption),
the cascade detector predicts which downstream domains will be
affected and provides root-cause hypotheses for multi-domain changes.

Example cascade:
  Sleep disruption (day 0)
    → Energy decline (day 0, weight 0.9)
    → Cognitive impairment (day 0, weight 0.85)
    → Stress elevation (day 0, weight 0.7)
    → Immune suppression (day 2, weight 0.6)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.domain.health_domains import HealthDomainKey
from app.domain.causal_graph import (
    DOMAIN_EDGES,
    DomainEdge,
    get_downstream_domains,
    get_upstream_domains,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CascadeStep:
    """One step in a predicted cascade."""
    domain: HealthDomainKey
    expected_lag_days: int
    expected_weight: float  # How strong the effect should be
    mechanism: str  # Why this domain is affected


@dataclass(frozen=True)
class CascadePrediction:
    """Predicted cascade from a trigger event."""
    trigger_domain: HealthDomainKey
    trigger_description: str
    steps: List[CascadeStep]
    total_domains_affected: int


@dataclass(frozen=True)
class DomainChange:
    """An observed change in a domain."""
    domain: HealthDomainKey
    direction: str  # "increase" | "decrease" | "disruption"
    magnitude: float  # Effect size
    when_detected: int  # Days ago


@dataclass(frozen=True)
class RootCauseHypothesis:
    """A hypothesis about what's causing multi-domain changes."""
    root_domain: HealthDomainKey
    confidence: float  # How well this explains the observations
    explained_domains: List[HealthDomainKey]
    unexplained_domains: List[HealthDomainKey]
    cascade_path: str  # Human-readable cascade description


class CascadeDetector:
    """
    Detects and explains cascading health effects across domains.

    Two main capabilities:
    1. predict_cascade: Given a trigger, what domains will be affected?
    2. explain_observations: Given multi-domain changes, find root cause.
    """

    def predict_cascade(
        self,
        trigger_domain: HealthDomainKey,
        trigger_description: str = "",
        max_depth: int = 2,
        min_weight: float = 0.1,
    ) -> CascadePrediction:
        """
        Predict downstream effects of a change in one domain.

        Args:
            trigger_domain: The domain where the change originated
            trigger_description: What happened (e.g., "sleep duration dropped 30%")
            max_depth: How many hops to follow in the graph
            min_weight: Minimum cumulative weight to include

        Returns:
            CascadePrediction with expected downstream effects
        """
        downstream = get_downstream_domains(trigger_domain, max_depth=max_depth)

        steps = [
            CascadeStep(
                domain=domain,
                expected_lag_days=lag,
                expected_weight=weight,
                mechanism=mechanism,
            )
            for domain, lag, weight, mechanism in downstream
            if weight >= min_weight
        ]

        return CascadePrediction(
            trigger_domain=trigger_domain,
            trigger_description=trigger_description,
            steps=steps,
            total_domains_affected=len(steps),
        )

    def explain_observations(
        self,
        observed_changes: List[DomainChange],
        max_depth: int = 2,
    ) -> List[RootCauseHypothesis]:
        """
        Given multi-domain changes, find the most likely root cause.

        For each observed change, check if it could be upstream of
        the other changes. The domain that explains the most observations
        with the best timing alignment is the most likely root cause.
        """
        if not observed_changes:
            return []

        changed_domains = {c.domain for c in observed_changes}
        hypotheses: List[RootCauseHypothesis] = []

        for candidate in observed_changes:
            # Get what this domain could affect
            downstream = get_downstream_domains(candidate.domain, max_depth=max_depth)
            downstream_domains = {d[0] for d in downstream}

            # How many other observed changes does this explain?
            explained = [
                c.domain for c in observed_changes
                if c.domain != candidate.domain and c.domain in downstream_domains
            ]
            unexplained = [
                c.domain for c in observed_changes
                if c.domain != candidate.domain and c.domain not in downstream_domains
            ]

            if not explained:
                continue

            # Confidence = proportion of other changes explained
            other_count = len(observed_changes) - 1
            if other_count == 0:
                continue
            confidence = len(explained) / other_count

            # Build path description
            path_parts = [f"{candidate.domain.value} ({candidate.direction})"]
            for domain, lag, weight, mechanism in downstream:
                if domain in set(explained):
                    path_parts.append(f"→ {domain.value} (lag {lag}d, weight {weight:.2f})")

            hypotheses.append(RootCauseHypothesis(
                root_domain=candidate.domain,
                confidence=confidence,
                explained_domains=explained,
                unexplained_domains=unexplained,
                cascade_path=" ".join(path_parts),
            ))

        # Sort by confidence descending
        hypotheses.sort(key=lambda h: h.confidence, reverse=True)
        return hypotheses

    def get_cascade_context_for_insight(
        self,
        domain: HealthDomainKey,
    ) -> Optional[str]:
        """
        Generate cascade context to embed in an insight.

        Returns a brief explanation of what upstream/downstream
        effects might be relevant for this domain.
        """
        upstream = get_upstream_domains(domain, max_depth=1)
        downstream = get_downstream_domains(domain, max_depth=1)

        if not upstream and not downstream:
            return None

        parts = []
        if upstream:
            top_upstream = upstream[:2]  # Top 2 contributors
            sources = [f"{d.value}" for d, _, _, _ in top_upstream]
            parts.append(f"This may be influenced by {', '.join(sources)}.")

        if downstream:
            top_downstream = downstream[:2]
            targets = [f"{d.value}" for d, _, _, _ in top_downstream]
            parts.append(f"This could affect {', '.join(targets)}.")

        return " ".join(parts)
