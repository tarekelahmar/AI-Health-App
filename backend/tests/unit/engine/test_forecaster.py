"""Tests for Phase 5.1: Short-Term Health Forecasting."""

import pytest
import numpy as np
from datetime import date, timedelta

from app.engine.forecasting.predictor import (
    HealthForecaster,
    PredictionPoint,
    Forecast,
    ForecastAccuracy,
    evaluate_forecast_accuracy,
    _holt_smooth,
    _prediction_interval,
    MIN_TRAINING_POINTS,
    MAX_HORIZON,
)


# ── Helpers ─────────────────────────────────────────────────────────


def _make_dates(n: int, start: date = date(2026, 1, 1)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


def _make_linear_series(n: int, slope: float = 1.0, intercept: float = 100.0, noise_std: float = 0.0):
    """Create a linear series with optional noise."""
    np.random.seed(42)
    values = [intercept + slope * i + np.random.normal(0, noise_std) for i in range(n)]
    return values


def _make_constant_series(n: int, value: float = 50.0):
    return [value] * n


# ── Test Holt Smoothing ────────────────────────────────────────────


class TestHoltSmoothing:
    """Test the exponential smoothing internals."""

    def test_constant_series_converges(self):
        """Level should converge to constant, trend to zero."""
        values = _make_constant_series(30, value=100.0)
        levels, trends, fitted = _holt_smooth(values)

        # After convergence, level should be ~100, trend ~0
        assert abs(levels[-1] - 100.0) < 1.0
        assert abs(trends[-1]) < 0.5

    def test_linear_series_tracks_trend(self):
        """Should pick up a linear trend."""
        values = _make_linear_series(30, slope=2.0, intercept=100.0)
        levels, trends, fitted = _holt_smooth(values)

        # Trend should be positive
        assert trends[-1] > 0.5

    def test_fitted_length_matches_input(self):
        values = _make_linear_series(20)
        levels, trends, fitted = _holt_smooth(values)
        assert len(levels) == 20
        assert len(trends) == 20
        assert len(fitted) == 20

    def test_high_alpha_more_reactive(self):
        """Higher alpha should follow recent values more closely."""
        np.random.seed(42)
        # Series with a sudden jump
        values = [100.0] * 15 + [150.0] * 15
        _, _, fitted_low = _holt_smooth(values, alpha=0.1)
        _, _, fitted_high = _holt_smooth(values, alpha=0.9)

        # At position 20 (5 steps after jump), high alpha should be closer to 150
        assert abs(fitted_high[20] - 150) < abs(fitted_low[20] - 150)


# ── Test HealthForecaster ──────────────────────────────────────────


class TestHealthForecaster:
    """Test the main forecasting engine."""

    @pytest.fixture
    def forecaster(self):
        return HealthForecaster()

    def test_insufficient_data_returns_none(self, forecaster):
        """Should return None if less than MIN_TRAINING_POINTS."""
        values = [100.0] * (MIN_TRAINING_POINTS - 1)
        dates = _make_dates(len(values))
        result = forecaster.forecast(values, dates, "hrv_rmssd_ms")
        assert result is None

    def test_minimum_data_produces_forecast(self, forecaster):
        """Should produce forecast with exactly MIN_TRAINING_POINTS."""
        values = _make_linear_series(MIN_TRAINING_POINTS, slope=1.0, intercept=50.0)
        dates = _make_dates(len(values))
        result = forecaster.forecast(values, dates, "hrv_rmssd_ms")

        assert result is not None
        assert result.metric == "hrv_rmssd_ms"
        assert len(result.predictions) == 3  # default horizon

    def test_forecast_has_correct_dates(self, forecaster):
        """Prediction dates should be sequential after last data date."""
        n = 20
        values = _make_linear_series(n)
        dates = _make_dates(n, start=date(2026, 2, 1))
        result = forecaster.forecast(values, dates, "test_metric")

        last_data_date = dates[-1]
        for i, pred in enumerate(result.predictions):
            expected_date = last_data_date + timedelta(days=i + 1)
            assert pred.target_date == expected_date

    def test_forecast_respects_horizon(self, forecaster):
        """Should produce exactly horizon_days predictions."""
        values = _make_linear_series(30)
        dates = _make_dates(30)

        for horizon in [1, 3, 5, 7]:
            result = forecaster.forecast(values, dates, "test", horizon_days=horizon)
            assert len(result.predictions) == horizon

    def test_forecast_caps_at_max_horizon(self, forecaster):
        """Horizon should be capped at MAX_HORIZON."""
        values = _make_linear_series(30)
        dates = _make_dates(30)
        result = forecaster.forecast(values, dates, "test", horizon_days=30)
        assert len(result.predictions) == MAX_HORIZON

    def test_upward_trend_forecasts_higher(self, forecaster):
        """Upward trending data should forecast higher values."""
        values = _make_linear_series(30, slope=2.0, intercept=100.0)
        dates = _make_dates(30)
        result = forecaster.forecast(values, dates, "test")

        last_value = values[-1]
        # Forecast should generally be above last value for upward trend
        assert result.predictions[0].predicted_value > last_value - 5

    def test_confidence_decreases_with_horizon(self, forecaster):
        """Later predictions should have lower confidence."""
        values = _make_linear_series(30)
        dates = _make_dates(30)
        result = forecaster.forecast(values, dates, "test", horizon_days=5)

        confidences = [p.confidence for p in result.predictions]
        # Each step should have equal or lower confidence
        for i in range(len(confidences) - 1):
            assert confidences[i] >= confidences[i + 1]

    def test_prediction_intervals_widen(self, forecaster):
        """Prediction intervals should widen with horizon."""
        values = _make_linear_series(30, noise_std=5.0)
        dates = _make_dates(30)
        result = forecaster.forecast(values, dates, "test", horizon_days=5)

        widths_80 = [p.ci_80[1] - p.ci_80[0] for p in result.predictions]
        widths_95 = [p.ci_95[1] - p.ci_95[0] for p in result.predictions]

        # Widths should increase
        for i in range(len(widths_80) - 1):
            assert widths_80[i + 1] >= widths_80[i] - 0.01  # small tolerance
            assert widths_95[i + 1] >= widths_95[i] - 0.01

    def test_95ci_wider_than_80ci(self, forecaster):
        """95% CI should always be wider than 80% CI."""
        values = _make_linear_series(30, noise_std=5.0)
        dates = _make_dates(30)
        result = forecaster.forecast(values, dates, "test", horizon_days=3)

        for pred in result.predictions:
            width_80 = pred.ci_80[1] - pred.ci_80[0]
            width_95 = pred.ci_95[1] - pred.ci_95[0]
            assert width_95 > width_80

    def test_constant_series_forecast_stable(self, forecaster):
        """Constant series should forecast near the constant value."""
        values = _make_constant_series(30, value=420.0)
        dates = _make_dates(30)
        result = forecaster.forecast(values, dates, "sleep_duration")

        for pred in result.predictions:
            assert abs(pred.predicted_value - 420.0) < 5.0

    def test_forecast_metadata(self, forecaster):
        """Forecast should include model metadata."""
        values = _make_linear_series(20)
        dates = _make_dates(20)
        result = forecaster.forecast(values, dates, "hrv")

        assert result.model_type == "holt_exponential_smoothing"
        assert result.n_training_points == 20
        assert result.training_mae >= 0
        assert len(result.features_used) > 0

    def test_mismatched_lengths_raises(self, forecaster):
        """Should raise ValueError if values and dates differ in length."""
        with pytest.raises(ValueError):
            forecaster.forecast([1.0, 2.0], [date(2026, 1, 1)], "test")


# ── Test Multiple Metric Forecasting ──────────────────────────────


class TestForecastMultiple:

    def test_forecasts_multiple_metrics(self):
        forecaster = HealthForecaster()
        n = 20
        dates = _make_dates(n)
        series = {
            "hrv": (_make_linear_series(n, slope=0.5), dates),
            "rhr": (_make_linear_series(n, slope=-0.2, intercept=65), dates),
        }
        results = forecaster.forecast_multiple(series)

        assert "hrv" in results
        assert "rhr" in results

    def test_skips_insufficient_data(self):
        forecaster = HealthForecaster()
        dates_short = _make_dates(5)
        dates_long = _make_dates(20)
        series = {
            "hrv": ([1.0] * 5, dates_short),  # Too short
            "rhr": (_make_linear_series(20), dates_long),  # OK
        }
        results = forecaster.forecast_multiple(series)

        assert "hrv" not in results
        assert "rhr" in results


# ── Test Accuracy Evaluation ──────────────────────────────────────


class TestForecastAccuracy:

    def test_perfect_prediction(self):
        """Perfect predictions should have zero MAE."""
        predictions = [
            PredictionPoint(
                target_date=date(2026, 3, 1) + timedelta(days=i),
                predicted_value=100.0 + i,
                ci_80=(95.0 + i, 105.0 + i),
                ci_95=(90.0 + i, 110.0 + i),
                confidence=0.9,
            )
            for i in range(3)
        ]
        actuals = [(date(2026, 3, 1) + timedelta(days=i), 100.0 + i) for i in range(3)]

        accuracy = evaluate_forecast_accuracy(predictions, actuals)
        assert accuracy is not None
        assert accuracy.mae == 0.0
        assert accuracy.coverage_80 == 1.0
        assert accuracy.coverage_95 == 1.0

    def test_no_matching_dates_returns_none(self):
        predictions = [
            PredictionPoint(
                target_date=date(2026, 3, 1),
                predicted_value=100.0,
                ci_80=(95.0, 105.0),
                ci_95=(90.0, 110.0),
                confidence=0.9,
            )
        ]
        actuals = [(date(2026, 4, 1), 100.0)]  # No date match
        assert evaluate_forecast_accuracy(predictions, actuals) is None

    def test_bias_positive_when_overpredicting(self):
        """Overprediction should give negative bias (actual - predicted < 0)."""
        predictions = [
            PredictionPoint(
                target_date=date(2026, 3, 1),
                predicted_value=110.0,
                ci_80=(105.0, 115.0),
                ci_95=(100.0, 120.0),
                confidence=0.9,
            )
        ]
        actuals = [(date(2026, 3, 1), 100.0)]
        accuracy = evaluate_forecast_accuracy(predictions, actuals)
        assert accuracy.bias < 0  # actual - predicted = 100 - 110 = -10

    def test_coverage_tracking(self):
        """Should correctly track interval coverage."""
        predictions = [
            PredictionPoint(
                target_date=date(2026, 3, 1),
                predicted_value=100.0,
                ci_80=(95.0, 105.0),
                ci_95=(90.0, 110.0),
                confidence=0.9,
            )
        ]
        # Actual within 80% CI
        actuals_in = [(date(2026, 3, 1), 102.0)]
        acc = evaluate_forecast_accuracy(predictions, actuals_in)
        assert acc.coverage_80 == 1.0
        assert acc.coverage_95 == 1.0

        # Actual outside 80% but within 95%
        actuals_between = [(date(2026, 3, 1), 108.0)]
        acc2 = evaluate_forecast_accuracy(predictions, actuals_between)
        assert acc2.coverage_80 == 0.0
        assert acc2.coverage_95 == 1.0


# ── Test Prediction Intervals ─────────────────────────────────────


class TestPredictionInterval:

    def test_interval_grows_with_horizon(self):
        """Interval should be wider for longer horizons."""
        hw1 = _prediction_interval(10.0, steps_ahead=1)
        hw3 = _prediction_interval(10.0, steps_ahead=3)
        hw7 = _prediction_interval(10.0, steps_ahead=7)
        assert hw3 > hw1
        assert hw7 > hw3

    def test_zero_std_gives_zero_interval(self):
        hw = _prediction_interval(0.0, steps_ahead=1)
        assert hw == 0.0

    def test_95_wider_than_80(self):
        hw_80 = _prediction_interval(10.0, steps_ahead=1, level=0.80)
        hw_95 = _prediction_interval(10.0, steps_ahead=1, level=0.95)
        assert hw_95 > hw_80
