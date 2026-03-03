"""
Domain Dependency Graph - Phase 4.1

Defines the causal relationships between the 10 canonical health domains.
These represent prior knowledge about how domains influence each other,
with typical lag times.

This is a PRIOR — the system refines these weights per user over time
based on observed correlations and experiment results.

Design:
- Deterministic, auditable, no ML
- Based on functional medicine literature
- Lags represent typical onset times
- Weights represent baseline expected strength
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.domain.health_domains import HealthDomainKey


@dataclass(frozen=True)
class DomainEdge:
    """A directed edge in the domain dependency graph."""
    source: HealthDomainKey
    target: HealthDomainKey
    typical_lag_days: int  # How long before effect manifests
    default_weight: float  # Prior strength (0-1)
    mechanism: str  # Short description of pathway


# The domain dependency graph
# Each entry: source domain → list of (target domain, lag_days, weight, mechanism)
DOMAIN_EDGES: List[DomainEdge] = [
    # Sleep affects many domains
    DomainEdge(HealthDomainKey.SLEEP, HealthDomainKey.ENERGY_FATIGUE, 0, 0.9,
               "Sleep debt directly impacts next-day energy"),
    DomainEdge(HealthDomainKey.SLEEP, HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE, 0, 0.85,
               "Sleep deprivation impairs cognitive function immediately"),
    DomainEdge(HealthDomainKey.SLEEP, HealthDomainKey.STRESS_NERVOUS_SYSTEM, 0, 0.7,
               "Poor sleep increases sympathetic tone"),
    DomainEdge(HealthDomainKey.SLEEP, HealthDomainKey.INFLAMMATION_IMMUNE, 2, 0.6,
               "Chronic sleep loss elevates inflammatory markers"),
    DomainEdge(HealthDomainKey.SLEEP, HealthDomainKey.HORMONAL_REPRODUCTIVE, 1, 0.5,
               "Sleep affects cortisol, testosterone, growth hormone"),

    # Stress cascades widely
    DomainEdge(HealthDomainKey.STRESS_NERVOUS_SYSTEM, HealthDomainKey.SLEEP, 0, 0.8,
               "Sympathetic activation disrupts sleep onset/quality"),
    DomainEdge(HealthDomainKey.STRESS_NERVOUS_SYSTEM, HealthDomainKey.GASTROINTESTINAL, 1, 0.7,
               "Vagal withdrawal impairs gut motility"),
    DomainEdge(HealthDomainKey.STRESS_NERVOUS_SYSTEM, HealthDomainKey.INFLAMMATION_IMMUNE, 3, 0.65,
               "Chronic cortisol dysregulates immune response"),
    DomainEdge(HealthDomainKey.STRESS_NERVOUS_SYSTEM, HealthDomainKey.HORMONAL_REPRODUCTIVE, 2, 0.6,
               "Cortisol steals from sex hormone production"),
    DomainEdge(HealthDomainKey.STRESS_NERVOUS_SYSTEM, HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE, 0, 0.6,
               "Acute stress impairs executive function"),

    # GI → systemic inflammation pathway
    DomainEdge(HealthDomainKey.GASTROINTESTINAL, HealthDomainKey.INFLAMMATION_IMMUNE, 2, 0.75,
               "Gut permeability drives systemic inflammation"),
    DomainEdge(HealthDomainKey.GASTROINTESTINAL, HealthDomainKey.ENERGY_FATIGUE, 1, 0.5,
               "Nutrient malabsorption impacts energy"),
    DomainEdge(HealthDomainKey.GASTROINTESTINAL, HealthDomainKey.HORMONAL_REPRODUCTIVE, 3, 0.4,
               "Gut-hormone axis affects estrogen metabolism"),

    # Inflammation cascades
    DomainEdge(HealthDomainKey.INFLAMMATION_IMMUNE, HealthDomainKey.ENERGY_FATIGUE, 1, 0.7,
               "Inflammatory cytokines cause sickness behavior/fatigue"),
    DomainEdge(HealthDomainKey.INFLAMMATION_IMMUNE, HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE, 1, 0.6,
               "Neuroinflammation impairs cognition"),
    DomainEdge(HealthDomainKey.INFLAMMATION_IMMUNE, HealthDomainKey.MUSCULOSKELETAL_RECOVERY, 1, 0.55,
               "Systemic inflammation delays tissue recovery"),
    DomainEdge(HealthDomainKey.INFLAMMATION_IMMUNE, HealthDomainKey.CARDIOMETABOLIC, 7, 0.5,
               "Chronic inflammation drives metabolic dysfunction"),

    # Cardiometabolic
    DomainEdge(HealthDomainKey.CARDIOMETABOLIC, HealthDomainKey.ENERGY_FATIGUE, 0, 0.6,
               "Metabolic efficiency affects energy production"),
    DomainEdge(HealthDomainKey.CARDIOMETABOLIC, HealthDomainKey.SLEEP, 1, 0.4,
               "Blood sugar dysregulation disrupts sleep"),

    # Hormonal
    DomainEdge(HealthDomainKey.HORMONAL_REPRODUCTIVE, HealthDomainKey.SLEEP, 0, 0.5,
               "Hormone fluctuations affect sleep architecture"),
    DomainEdge(HealthDomainKey.HORMONAL_REPRODUCTIVE, HealthDomainKey.ENERGY_FATIGUE, 0, 0.55,
               "Hormone levels modulate energy and motivation"),
    DomainEdge(HealthDomainKey.HORMONAL_REPRODUCTIVE, HealthDomainKey.STRESS_NERVOUS_SYSTEM, 0, 0.45,
               "Hormone changes affect stress sensitivity"),

    # Nutrition
    DomainEdge(HealthDomainKey.NUTRITION_MICRONUTRIENTS, HealthDomainKey.GASTROINTESTINAL, 1, 0.6,
               "Diet composition affects gut health"),
    DomainEdge(HealthDomainKey.NUTRITION_MICRONUTRIENTS, HealthDomainKey.INFLAMMATION_IMMUNE, 2, 0.55,
               "Dietary patterns modulate inflammation"),
    DomainEdge(HealthDomainKey.NUTRITION_MICRONUTRIENTS, HealthDomainKey.ENERGY_FATIGUE, 0, 0.65,
               "Macro/micronutrient availability affects energy"),

    # Musculoskeletal
    DomainEdge(HealthDomainKey.MUSCULOSKELETAL_RECOVERY, HealthDomainKey.SLEEP, 0, 0.4,
               "Exercise and soreness can disrupt or improve sleep"),
    DomainEdge(HealthDomainKey.MUSCULOSKELETAL_RECOVERY, HealthDomainKey.STRESS_NERVOUS_SYSTEM, 0, 0.5,
               "Training load affects autonomic balance"),
    DomainEdge(HealthDomainKey.MUSCULOSKELETAL_RECOVERY, HealthDomainKey.INFLAMMATION_IMMUNE, 1, 0.4,
               "Intense training transiently elevates inflammation"),

    # Energy/cognitive feedback
    DomainEdge(HealthDomainKey.ENERGY_FATIGUE, HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE, 0, 0.7,
               "Low energy impairs focus and cognitive performance"),
    DomainEdge(HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE, HealthDomainKey.STRESS_NERVOUS_SYSTEM, 0, 0.35,
               "Cognitive overload contributes to perceived stress"),
]


def get_downstream_domains(
    source: HealthDomainKey,
    max_depth: int = 2,
) -> List[Tuple[HealthDomainKey, int, float, str]]:
    """
    Get all domains downstream of source, with BFS to max_depth.

    Returns list of (domain, lag_days, cumulative_weight, path_description).
    """
    # Build adjacency list
    adj: Dict[HealthDomainKey, List[DomainEdge]] = {}
    for edge in DOMAIN_EDGES:
        adj.setdefault(edge.source, []).append(edge)

    results = []
    visited = {source}
    queue = [(source, 0, 1.0, [])]  # (node, total_lag, cumulative_weight, path)

    while queue:
        current, lag, weight, path = queue.pop(0)

        for edge in adj.get(current, []):
            if edge.target in visited:
                continue
            visited.add(edge.target)

            new_lag = lag + edge.typical_lag_days
            new_weight = weight * edge.default_weight
            new_path = path + [edge.mechanism]

            results.append((edge.target, new_lag, new_weight, " → ".join(new_path)))

            if len(path) < max_depth - 1:
                queue.append((edge.target, new_lag, new_weight, new_path))

    # Sort by weight descending
    results.sort(key=lambda x: x[2], reverse=True)
    return results


def get_upstream_domains(
    target: HealthDomainKey,
    max_depth: int = 2,
) -> List[Tuple[HealthDomainKey, int, float, str]]:
    """
    Get all domains upstream of target (what could be causing issues).

    Returns list of (domain, lag_days, cumulative_weight, path_description).
    """
    # Build reverse adjacency list
    rev_adj: Dict[HealthDomainKey, List[DomainEdge]] = {}
    for edge in DOMAIN_EDGES:
        rev_adj.setdefault(edge.target, []).append(edge)

    results = []
    visited = {target}
    queue = [(target, 0, 1.0, [])]

    while queue:
        current, lag, weight, path = queue.pop(0)

        for edge in rev_adj.get(current, []):
            if edge.source in visited:
                continue
            visited.add(edge.source)

            new_lag = lag + edge.typical_lag_days
            new_weight = weight * edge.default_weight
            new_path = [edge.mechanism] + path

            results.append((edge.source, new_lag, new_weight, " → ".join(new_path)))

            if len(path) < max_depth - 1:
                queue.append((edge.source, new_lag, new_weight, new_path))

    results.sort(key=lambda x: x[2], reverse=True)
    return results


def get_direct_edges(domain: HealthDomainKey) -> Dict[str, List[DomainEdge]]:
    """Get direct edges to and from a domain."""
    outgoing = [e for e in DOMAIN_EDGES if e.source == domain]
    incoming = [e for e in DOMAIN_EDGES if e.target == domain]
    return {"outgoing": outgoing, "incoming": incoming}
