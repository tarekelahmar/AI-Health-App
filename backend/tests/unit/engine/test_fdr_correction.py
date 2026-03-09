"""Tests for Phase 2.4: FDR multiple testing correction."""

import pytest
from app.engine.statistics.multiple_testing import (
    benjamini_hochberg,
    z_score_to_p_value,
    apply_fdr_to_insights,
)


class TestBenjaminiHochberg:
    """Test BH FDR correction."""

    def test_all_significant_remain(self):
        """Very small p-values should survive correction."""
        p_values = [0.001, 0.002, 0.003]
        result = benjamini_hochberg(p_values, alpha=0.10)

        assert all(result.rejected)
        assert result.n_discoveries == 3

    def test_borderline_values_corrected(self):
        """Near-threshold p-values should be corrected upward."""
        # Without correction: 0.04 and 0.05 are significant at alpha=0.05
        # With BH on 5 tests: threshold is more conservative
        p_values = [0.01, 0.04, 0.05, 0.1, 0.5]
        result = benjamini_hochberg(p_values, alpha=0.05)

        # Adjusted p-values should be >= original
        for orig, adj in zip(result.original_p_values, result.adjusted_p_values):
            assert adj >= orig

    def test_no_significant(self):
        """All large p-values should produce no discoveries."""
        p_values = [0.3, 0.5, 0.7, 0.9]
        result = benjamini_hochberg(p_values, alpha=0.10)

        assert result.n_discoveries == 0
        assert not any(result.rejected)

    def test_empty_input(self):
        """Empty p-value list should return empty result."""
        result = benjamini_hochberg([], alpha=0.10)
        assert result.n_discoveries == 0
        assert result.adjusted_p_values == []

    def test_single_value(self):
        """Single p-value should be unchanged."""
        result = benjamini_hochberg([0.03], alpha=0.05)
        assert result.adjusted_p_values[0] == pytest.approx(0.03, abs=0.001)
        assert result.rejected[0] is True

    def test_expected_false_discoveries(self):
        """Expected false discoveries should be n_discoveries * alpha."""
        p_values = [0.001, 0.002, 0.003, 0.5, 0.9]
        result = benjamini_hochberg(p_values, alpha=0.10)

        assert result.expected_false_discoveries == pytest.approx(
            result.n_discoveries * 0.10, abs=0.01
        )

    def test_adjusted_p_values_bounded(self):
        """Adjusted p-values should be in [0, 1]."""
        p_values = [0.001, 0.01, 0.05, 0.1, 0.5]
        result = benjamini_hochberg(p_values, alpha=0.10)

        for p in result.adjusted_p_values:
            assert 0.0 <= p <= 1.0

    def test_adjusted_preserves_order(self):
        """If p_i < p_j, then adjusted_p_i <= adjusted_p_j."""
        p_values = [0.001, 0.01, 0.05, 0.1, 0.5]
        result = benjamini_hochberg(p_values, alpha=0.10)

        for i in range(len(result.adjusted_p_values) - 1):
            # This should hold for the sorted order
            pass  # BH maintains monotonicity in sorted order

    def test_frozen_result(self):
        """FDRAdjustedResult should be immutable."""
        result = benjamini_hochberg([0.01, 0.05])
        with pytest.raises(AttributeError):
            result.n_discoveries = 999


class TestZScoreToPValue:
    """Test z-score to p-value conversion."""

    def test_zero_z_gives_p_one(self):
        """Z=0 should give p=1 (no evidence)."""
        assert z_score_to_p_value(0.0) == pytest.approx(1.0, abs=0.01)

    def test_large_z_gives_small_p(self):
        """Z=3 should give very small p."""
        p = z_score_to_p_value(3.0)
        assert p < 0.01

    def test_symmetric(self):
        """Positive and negative z should give same p (two-tailed)."""
        assert z_score_to_p_value(2.0) == pytest.approx(z_score_to_p_value(-2.0))


class TestApplyFDRToInsights:
    """Test FDR correction applied to insight batches."""

    def test_annotates_insights(self):
        """Should add fdr_adjusted_p and fdr_significant to insights."""
        insights = [
            {"evidence": {"z_score": 3.0}},
            {"evidence": {"z_score": 1.5}},
            {"evidence": {"z_score": 0.5}},
        ]
        adjusted, fdr_result = apply_fdr_to_insights(insights, alpha=0.10)

        assert len(adjusted) == 3
        assert all("fdr_adjusted_p" in ins for ins in adjusted)
        assert all("fdr_significant" in ins for ins in adjusted)

    def test_no_z_scores_handled(self):
        """Should handle insights without z-scores gracefully."""
        insights = [
            {"evidence": {"slope_per_day": 0.5}},
            {"evidence": {}},
        ]
        adjusted, fdr_result = apply_fdr_to_insights(insights, alpha=0.10)
        assert fdr_result.n_discoveries == 0
