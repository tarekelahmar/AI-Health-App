"""Tests for Phase 4.1: Domain Dependency Graph and Cascade Detection."""

import pytest
from app.domain.health_domains import HealthDomainKey
from app.domain.causal_graph import (
    DOMAIN_EDGES,
    DomainEdge,
    get_downstream_domains,
    get_upstream_domains,
    get_direct_edges,
)
from app.engine.reasoning.cascade_detector import (
    CascadeDetector,
    DomainChange,
)


class TestDomainGraph:
    """Test the domain dependency graph structure."""

    def test_all_edges_reference_valid_domains(self):
        """Every edge should reference valid HealthDomainKeys."""
        valid = set(HealthDomainKey)
        for edge in DOMAIN_EDGES:
            assert edge.source in valid, f"Invalid source: {edge.source}"
            assert edge.target in valid, f"Invalid target: {edge.target}"

    def test_no_self_loops(self):
        """No domain should have an edge to itself."""
        for edge in DOMAIN_EDGES:
            assert edge.source != edge.target, f"Self-loop: {edge.source}"

    def test_weights_bounded(self):
        """All weights should be in (0, 1]."""
        for edge in DOMAIN_EDGES:
            assert 0 < edge.default_weight <= 1.0, (
                f"Bad weight {edge.default_weight} for {edge.source}→{edge.target}"
            )

    def test_lags_non_negative(self):
        """All lags should be >= 0."""
        for edge in DOMAIN_EDGES:
            assert edge.typical_lag_days >= 0

    def test_all_edges_have_mechanism(self):
        """Every edge should have a mechanism description."""
        for edge in DOMAIN_EDGES:
            assert edge.mechanism and len(edge.mechanism) > 10

    def test_sleep_has_many_downstream(self):
        """Sleep should affect multiple domains (core health driver)."""
        downstream = get_downstream_domains(HealthDomainKey.SLEEP, max_depth=1)
        assert len(downstream) >= 3

    def test_stress_has_many_downstream(self):
        """Stress should cascade widely."""
        downstream = get_downstream_domains(HealthDomainKey.STRESS_NERVOUS_SYSTEM, max_depth=1)
        assert len(downstream) >= 4

    def test_energy_has_upstream_causes(self):
        """Energy should have multiple upstream causes."""
        upstream = get_upstream_domains(HealthDomainKey.ENERGY_FATIGUE, max_depth=1)
        assert len(upstream) >= 3

    def test_downstream_depth_2_more_results(self):
        """Depth 2 BFS should find more domains than depth 1."""
        d1 = get_downstream_domains(HealthDomainKey.SLEEP, max_depth=1)
        d2 = get_downstream_domains(HealthDomainKey.SLEEP, max_depth=2)
        assert len(d2) >= len(d1)

    def test_cumulative_weight_decreases(self):
        """Multi-hop paths should have lower cumulative weight."""
        downstream = get_downstream_domains(HealthDomainKey.SLEEP, max_depth=2)
        # Direct edges have weight >= second-hop edges
        direct = [d for d in downstream if d[2] > 0.5]
        indirect = [d for d in downstream if d[2] <= 0.3]
        # At least some indirect paths should exist
        if indirect:
            assert max(d[2] for d in direct) > max(d[2] for d in indirect)


class TestDirectEdges:
    """Test direct edge lookup."""

    def test_sleep_edges(self):
        edges = get_direct_edges(HealthDomainKey.SLEEP)
        assert len(edges["outgoing"]) >= 3
        assert len(edges["incoming"]) >= 1  # Stress affects sleep


class TestCascadeDetector:
    """Test cascade prediction and root cause analysis."""

    @pytest.fixture
    def detector(self):
        return CascadeDetector()

    def test_predict_sleep_cascade(self, detector):
        """Sleep disruption should predict energy + cognitive effects."""
        prediction = detector.predict_cascade(
            HealthDomainKey.SLEEP,
            "Sleep duration dropped 30%",
        )
        affected = [s.domain for s in prediction.steps]
        assert HealthDomainKey.ENERGY_FATIGUE in affected
        assert HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE in affected
        assert prediction.total_domains_affected >= 3

    def test_predict_stress_cascade(self, detector):
        """Stress should predict gut + sleep effects."""
        prediction = detector.predict_cascade(
            HealthDomainKey.STRESS_NERVOUS_SYSTEM,
            "Stress elevated for 2 weeks",
        )
        affected = [s.domain for s in prediction.steps]
        assert HealthDomainKey.SLEEP in affected
        assert HealthDomainKey.GASTROINTESTINAL in affected

    def test_cascade_steps_have_lag(self, detector):
        """Cascade steps should include expected lag."""
        prediction = detector.predict_cascade(HealthDomainKey.SLEEP)
        for step in prediction.steps:
            assert step.expected_lag_days >= 0
            assert step.expected_weight > 0
            assert len(step.mechanism) > 0

    def test_explain_multi_domain_changes(self, detector):
        """Should identify sleep as root cause of energy + cognitive decline."""
        changes = [
            DomainChange(HealthDomainKey.SLEEP, "decrease", 0.8, 3),
            DomainChange(HealthDomainKey.ENERGY_FATIGUE, "decrease", 0.6, 2),
            DomainChange(HealthDomainKey.COGNITIVE_MENTAL_PERFORMANCE, "decrease", 0.5, 2),
        ]
        hypotheses = detector.explain_observations(changes)

        assert len(hypotheses) >= 1
        # Sleep should be the top hypothesis (explains energy + cognitive)
        assert hypotheses[0].root_domain == HealthDomainKey.SLEEP
        assert hypotheses[0].confidence > 0.5

    def test_explain_empty_returns_empty(self, detector):
        hypotheses = detector.explain_observations([])
        assert hypotheses == []

    def test_cascade_context_for_insight(self, detector):
        """Should generate context string for insights."""
        context = detector.get_cascade_context_for_insight(
            HealthDomainKey.ENERGY_FATIGUE
        )
        assert context is not None
        assert len(context) > 20
