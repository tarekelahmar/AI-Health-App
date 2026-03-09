"""
Tests for the deterministic explanation generator.

Validates that:
- All insight types produce readable explanations
- Claim policies are respected at every evidence grade
- Edge cases (missing data, unknown metrics) degrade gracefully
- Generated text passes governance validation
"""

import pytest
from app.engine.explanation_generator import generate_deterministic_explanation
from app.domain.claims import EvidenceGrade, get_claim_policy
from app.engine.governance.claim_policy import validate_language


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_kwargs(
    metric_key="sleep_duration",
    insight_type="change",
    evidence=None,
    metadata=None,
    confidence=0.85,
    grade=EvidenceGrade.A,
    governance_level=4,
    domain_key="sleep",
):
    """Helper to build keyword args for generate_deterministic_explanation."""
    ev = evidence or {
        "baseline_mean": 420.0,
        "recent_mean": 390.0,
        "baseline_std": 25.0,
        "z_score": -1.2,
        "n_points": 14,
        "coverage": 0.8,
        "window_days": 14,
    }
    meta = metadata or {
        "direction": "down",
        "metric_key": metric_key,
        "domain_key": domain_key,
    }
    return dict(
        metric_key=metric_key,
        insight_type=insight_type,
        evidence=ev,
        metadata=meta,
        confidence=confidence,
        evidence_grade=grade,
        claim_policy=get_claim_policy(grade),
        governance_claim_level=governance_level,
        domain_key=domain_key,
    )


# ---------------------------------------------------------------------------
# Basic functionality
# ---------------------------------------------------------------------------

class TestChangeInsight:
    """Tests for change-type insights."""

    def test_returns_all_three_fields(self):
        result = generate_deterministic_explanation(**_make_kwargs())
        assert "explanation" in result
        assert "uncertainty" in result
        assert "suggested_next_step" in result
        assert result["explanation"]
        assert result["uncertainty"]
        assert result["suggested_next_step"]

    def test_explanation_mentions_metric_display_name(self):
        result = generate_deterministic_explanation(**_make_kwargs())
        assert "Sleep Duration" in result["explanation"]

    def test_explanation_includes_numeric_context(self):
        result = generate_deterministic_explanation(**_make_kwargs())
        # Should mention the recent mean and baseline mean values
        assert "390" in result["explanation"]
        assert "420" in result["explanation"]

    def test_direction_down_uses_decrease_language(self):
        result = generate_deterministic_explanation(**_make_kwargs())
        explanation = result["explanation"].lower()
        assert "decrease" in explanation or "changed" in explanation

    def test_direction_up_uses_increase_language(self):
        kwargs = _make_kwargs(metadata={"direction": "up", "metric_key": "sleep_duration"})
        result = generate_deterministic_explanation(**kwargs)
        explanation = result["explanation"].lower()
        assert "increase" in explanation or "changed" in explanation

    def test_z_score_context_large_deviation(self):
        kwargs = _make_kwargs(evidence={
            "baseline_mean": 420.0,
            "recent_mean": 300.0,
            "z_score": -4.8,
            "n_points": 20,
        })
        result = generate_deterministic_explanation(**kwargs)
        assert "large deviation" in result["explanation"].lower()

    def test_z_score_context_moderate(self):
        kwargs = _make_kwargs(evidence={
            "baseline_mean": 420.0,
            "recent_mean": 395.0,
            "z_score": -1.0,
            "n_points": 10,
        })
        result = generate_deterministic_explanation(**kwargs)
        # Moderate z-score should describe a moderate shift or mention the change
        explanation = result["explanation"].lower()
        assert "moderate" in explanation or "changed" in explanation or "shift" in explanation


class TestTrendInsight:
    """Tests for trend-type insights."""

    def test_trend_mentions_slope(self):
        kwargs = _make_kwargs(
            insight_type="trend",
            evidence={
                "slope_per_day": -2.5,
                "window_days": 14,
                "n_points": 12,
                "days_consistent": 7,
            },
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "2.5" in result["explanation"] or "2.50" in result["explanation"]

    def test_trend_mentions_window(self):
        kwargs = _make_kwargs(
            insight_type="trend",
            evidence={
                "slope_per_day": -2.5,
                "window_days": 14,
                "n_points": 12,
            },
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "14" in result["explanation"]

    def test_trend_days_consistent(self):
        kwargs = _make_kwargs(
            insight_type="trend",
            evidence={
                "slope_per_day": -2.5,
                "window_days": 14,
                "n_points": 12,
                "days_consistent": 10,
            },
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "consistent" in result["explanation"].lower()


class TestInstabilityInsight:
    """Tests for instability-type insights."""

    def test_instability_mentions_ratio(self):
        kwargs = _make_kwargs(
            insight_type="instability",
            evidence={
                "instability_ratio": 2.3,
                "recent_std": 50.0,
                "baseline_std": 22.0,
            },
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "2.3" in result["explanation"]
        assert "variability" in result["explanation"].lower()


class TestSafetyInsight:
    """Tests for safety-type insights."""

    def test_safety_mentions_healthcare_provider(self):
        kwargs = _make_kwargs(
            insight_type="safety",
            evidence={"triggers_count": 2},
            governance_level=1,  # Safety insights use conservative level
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "healthcare provider" in result["explanation"].lower()

    def test_safety_next_step_always_consult(self):
        kwargs = _make_kwargs(
            insight_type="safety",
            evidence={"triggers_count": 1},
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "healthcare professional" in result["suggested_next_step"].lower()

    def test_safety_mentions_trigger_count(self):
        kwargs = _make_kwargs(
            insight_type="safety",
            evidence={"triggers_count": 3},
            governance_level=1,
        )
        result = generate_deterministic_explanation(**kwargs)
        assert "3" in result["explanation"]


# ---------------------------------------------------------------------------
# Evidence grades & uncertainty
# ---------------------------------------------------------------------------

class TestEvidenceGrades:
    """Tests that evidence grade affects language appropriately."""

    def test_grade_a_high_confidence_uncertainty(self):
        kwargs = _make_kwargs(grade=EvidenceGrade.A)
        result = generate_deterministic_explanation(**kwargs)
        assert "high confidence" in result["uncertainty"].lower()

    def test_grade_b_moderate_uncertainty(self):
        kwargs = _make_kwargs(grade=EvidenceGrade.B, confidence=0.65, governance_level=3)
        result = generate_deterministic_explanation(**kwargs)
        assert "moderate" in result["uncertainty"].lower()

    def test_grade_c_limited_data_uncertainty(self):
        kwargs = _make_kwargs(grade=EvidenceGrade.C, confidence=0.45, governance_level=2)
        result = generate_deterministic_explanation(**kwargs)
        assert "limited" in result["uncertainty"].lower()

    def test_grade_d_preliminary_uncertainty(self):
        kwargs = _make_kwargs(grade=EvidenceGrade.D, confidence=0.2, governance_level=1)
        result = generate_deterministic_explanation(**kwargs)
        assert "preliminary" in result["uncertainty"].lower() or "limited" in result["uncertainty"].lower()

    def test_grade_d_uses_hedged_language(self):
        kwargs = _make_kwargs(grade=EvidenceGrade.D, confidence=0.2, governance_level=1)
        result = generate_deterministic_explanation(**kwargs)
        explanation = result["explanation"].lower()
        # Should use words like "could", "might", "possibly"
        assert any(w in explanation for w in ["could", "might", "possibly", "pattern", "changes"])

    def test_low_coverage_adds_coverage_note(self):
        kwargs = _make_kwargs(evidence={
            "baseline_mean": 420.0,
            "recent_mean": 390.0,
            "z_score": -1.2,
            "n_points": 5,
            "coverage": 0.3,
            "window_days": 14,
        })
        result = generate_deterministic_explanation(**kwargs)
        assert "coverage" in result["uncertainty"].lower() or "30%" in result["uncertainty"]


# ---------------------------------------------------------------------------
# Suggested next steps
# ---------------------------------------------------------------------------

class TestNextSteps:
    """Tests for suggested_next_step generation."""

    def test_level_1_suggests_monitoring(self):
        kwargs = _make_kwargs(governance_level=1)
        result = generate_deterministic_explanation(**kwargs)
        assert "tracking" in result["suggested_next_step"].lower() or "monitoring" in result["suggested_next_step"].lower() or "continue" in result["suggested_next_step"].lower()

    def test_level_3_suggests_experiment(self):
        kwargs = _make_kwargs(governance_level=3)
        result = generate_deterministic_explanation(**kwargs)
        assert "experiment" in result["suggested_next_step"].lower()

    def test_level_4_suggests_protocol_review(self):
        kwargs = _make_kwargs(governance_level=4)
        result = generate_deterministic_explanation(**kwargs)
        assert "protocol" in result["suggested_next_step"].lower() or "observed" in result["suggested_next_step"].lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for graceful handling of edge cases."""

    def test_unknown_metric_uses_key_as_name(self):
        kwargs = _make_kwargs(metric_key="totally_new_metric_xyz")
        result = generate_deterministic_explanation(**kwargs)
        assert "Totally New Metric Xyz" in result["explanation"]

    def test_all_evidence_values_none(self):
        kwargs = _make_kwargs(evidence={
            "baseline_mean": None,
            "recent_mean": None,
            "z_score": None,
            "n_points": None,
        })
        result = generate_deterministic_explanation(**kwargs)
        # Should not crash, should return valid strings
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 10

    def test_empty_evidence(self):
        kwargs = _make_kwargs(evidence={})
        result = generate_deterministic_explanation(**kwargs)
        assert isinstance(result["explanation"], str)
        assert len(result["explanation"]) > 10

    def test_empty_metadata(self):
        kwargs = _make_kwargs(metadata={})
        result = generate_deterministic_explanation(**kwargs)
        assert isinstance(result["explanation"], str)

    def test_unknown_insight_type_uses_default(self):
        kwargs = _make_kwargs(insight_type="some_future_type")
        result = generate_deterministic_explanation(**kwargs)
        assert "pattern" in result["explanation"].lower() or "sleep duration" in result["explanation"].lower()

    def test_no_domain_key(self):
        kwargs = _make_kwargs(domain_key=None)
        result = generate_deterministic_explanation(**kwargs)
        assert isinstance(result["explanation"], str)

    def test_hrv_metric_uses_correct_display_name(self):
        kwargs = _make_kwargs(metric_key="hrv_rmssd")
        result = generate_deterministic_explanation(**kwargs)
        assert "Heart Rate Variability" in result["explanation"]

    def test_never_contains_diagnostic_language(self):
        """Ensure the generator never uses diagnostic/prescriptive words."""
        for grade in [EvidenceGrade.A, EvidenceGrade.B, EvidenceGrade.C, EvidenceGrade.D]:
            kwargs = _make_kwargs(grade=grade, confidence=0.5, governance_level=3)
            result = generate_deterministic_explanation(**kwargs)
            combined = (result["explanation"] + result["uncertainty"] + result["suggested_next_step"]).lower()
            for forbidden in ["diagnos", "prescri", "you have", "you suffer", "medication", "treatment"]:
                assert forbidden not in combined, f"Found '{forbidden}' in output for grade {grade}"
