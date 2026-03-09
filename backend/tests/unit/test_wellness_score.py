"""Tests for the wellness score computation engine."""

import pytest

from app.engine.wellness_score import (
    compute_wellness_score,
    _z_to_score,
    WellnessScoreResult,
    BASELINE_SCORE,
)


class TestZToScore:
    """Test z-score to wellness score mapping."""

    def test_zero_z_maps_to_baseline(self):
        assert _z_to_score(0.0) == BASELINE_SCORE  # 70

    def test_positive_z_increases_score(self):
        score = _z_to_score(2.0)
        assert score == 95.0  # 70 + 2*12.5

    def test_negative_z_decreases_score(self):
        score = _z_to_score(-2.0)
        assert score == 45.0  # 70 - 2*12.5

    def test_score_clamped_at_minimum(self):
        score = _z_to_score(-10.0)
        assert score == 5.0

    def test_score_clamped_at_maximum(self):
        score = _z_to_score(10.0)
        assert score == 99.0


class TestComputeWellnessScore:
    """Test the full wellness score computation."""

    def test_at_baseline_returns_70(self):
        """When all metrics are at baseline, score should be ~70."""
        baselines = {
            "hrv_rmssd": (50.0, 10.0),
            "sleep_duration": (450.0, 30.0),
            "energy": (3.0, 0.5),
            "mood": (3.0, 0.5),
        }
        objective = {"hrv_rmssd": 50.0, "sleep_duration": 450.0}
        subjective = {"energy": 3.0, "mood": 3.0}

        result = compute_wellness_score(objective, subjective, baselines)

        assert isinstance(result, WellnessScoreResult)
        assert result.score == BASELINE_SCORE  # 70.0

    def test_above_baseline_gives_higher_score(self):
        """When metrics are above baseline, score should be > 70."""
        baselines = {
            "hrv_rmssd": (50.0, 10.0),
            "energy": (3.0, 0.5),
        }
        objective = {"hrv_rmssd": 70.0}  # +2 std above baseline
        subjective = {"energy": 4.0}  # +2 std above

        result = compute_wellness_score(objective, subjective, baselines)

        assert result.score > 70

    def test_below_baseline_gives_lower_score(self):
        """When metrics are below baseline, score should be < 70."""
        baselines = {
            "hrv_rmssd": (50.0, 10.0),
            "energy": (3.0, 0.5),
        }
        objective = {"hrv_rmssd": 30.0}  # -2 std below
        subjective = {"energy": 2.0}  # -2 std below

        result = compute_wellness_score(objective, subjective, baselines)

        assert result.score < 70

    def test_lower_is_better_metrics_flipped(self):
        """Stress is lower_better, so low stress = high score."""
        baselines = {
            "stress": (3.0, 0.5),
        }
        # Low stress (good) should give positive contribution
        result = compute_wellness_score({}, {"stress": 2.0}, baselines)
        assert result.score > 70

        # High stress (bad) should give negative contribution
        result = compute_wellness_score({}, {"stress": 4.0}, baselines)
        assert result.score < 70

    def test_rhr_lower_is_better(self):
        """Resting HR is lower_better, so low RHR = high score."""
        baselines = {
            "resting_hr": (65.0, 5.0),
        }
        # Low RHR (good)
        result = compute_wellness_score({"resting_hr": 55.0}, {}, baselines)
        assert result.score > 70

        # High RHR (bad)
        result = compute_wellness_score({"resting_hr": 75.0}, {}, baselines)
        assert result.score < 70

    def test_objective_only_uses_full_weight(self):
        """When only objective data present, use 100% of it."""
        baselines = {"hrv_rmssd": (50.0, 10.0)}
        result = compute_wellness_score({"hrv_rmssd": 60.0}, {}, baselines)

        assert result.score > 70
        assert result.objective_score is not None
        assert result.subjective_score is None

    def test_subjective_only_uses_full_weight(self):
        """When only subjective data present, use 100% of it."""
        baselines = {"mood": (3.0, 0.5)}
        result = compute_wellness_score({}, {"mood": 4.0}, baselines)

        assert result.score > 70
        assert result.objective_score is None
        assert result.subjective_score is not None

    def test_no_data_returns_baseline(self):
        """When no data at all, return baseline score."""
        result = compute_wellness_score({}, {}, {})

        assert result.score == BASELINE_SCORE
        assert result.objective_score is None
        assert result.subjective_score is None
        assert len(result.contributing_factors) == 0

    def test_no_baselines_returns_baseline(self):
        """When metrics have values but no baselines, return baseline."""
        result = compute_wellness_score(
            {"hrv_rmssd": 50.0}, {"energy": 3.0}, {}
        )

        assert result.score == BASELINE_SCORE

    def test_contributing_factors_populated(self):
        """Each metric should produce a contributing factor."""
        baselines = {
            "hrv_rmssd": (50.0, 10.0),
            "energy": (3.0, 0.5),
            "mood": (3.0, 0.5),
        }
        result = compute_wellness_score(
            {"hrv_rmssd": 55.0},
            {"energy": 3.5, "mood": 2.5},
            baselines,
        )

        assert len(result.contributing_factors) == 3
        keys = {f.metric_key for f in result.contributing_factors}
        assert keys == {"hrv_rmssd", "energy", "mood"}

    def test_contributing_factors_have_correct_direction(self):
        baselines = {
            "energy": (3.0, 0.5),
            "mood": (3.0, 0.5),
        }
        result = compute_wellness_score(
            {},
            {"energy": 4.0, "mood": 2.0},
            baselines,
        )

        energy_f = next(f for f in result.contributing_factors if f.metric_key == "energy")
        mood_f = next(f for f in result.contributing_factors if f.metric_key == "mood")

        assert energy_f.direction == "positive"
        assert mood_f.direction == "negative"

    def test_60_40_weighting(self):
        """Verify objective gets 60% weight, subjective gets 40%."""
        baselines = {
            "hrv_rmssd": (50.0, 10.0),
            "energy": (3.0, 0.5),
        }

        # Objective: +2z (good), subjective: -2z (bad)
        result = compute_wellness_score(
            {"hrv_rmssd": 70.0},
            {"energy": 2.0},
            baselines,
        )

        # Composite should be slightly positive: 0.6*2 + 0.4*(-2) = 0.4
        assert result.score > 70  # Net positive
        # But not as high as if both were positive
        pure_obj = compute_wellness_score({"hrv_rmssd": 70.0}, {}, baselines)
        assert result.score < pure_obj.score

    def test_zero_spread_handled(self):
        """Very small spread shouldn't cause division errors."""
        baselines = {"energy": (3.0, 0.0)}
        result = compute_wellness_score({}, {"energy": 3.5}, baselines)
        # Should not crash, spread fallback to 0.1
        assert result.score > 0
