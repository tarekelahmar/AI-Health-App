"""
Short-term health metric forecasting engine.

Phase 5.1: Generates 1-7 day forecasts for health metrics using
exponential smoothing with personal baseline integration.

Approach:
  - Holt's linear exponential smoothing (level + trend)
  - Prediction intervals from forecast error distribution
  - Accuracy tracking via MAE/MAPE on rolling holdouts

Why not ARIMA: Exponential smoothing is robust with short, noisy
health time-series (often < 60 data points). ARIMA needs stationarity
checks, differencing, and parameter tuning that adds complexity
without clear benefit at these data scales.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Data Classes ────────────────────────────────────────────────────


@dataclass(frozen=True)
class PredictionPoint:
    """A single forecast point with confidence interval."""
    target_date: date
    predicted_value: float
    ci_80: Tuple[float, float]  # 80% prediction interval
    ci_95: Tuple[float, float]  # 95% prediction interval
    confidence: float  # 0-1, how much to trust this point


@dataclass(frozen=True)
class Forecast:
    """Complete forecast result for a metric."""
    metric: str
    generated_date: date
    predictions: List[PredictionPoint]
    model_type: str
    n_training_points: int
    training_mae: float  # In-sample MAE for calibration
    features_used: List[str] = field(default_factory=list)


@dataclass
class ForecastAccuracy:
    """Tracks forecast accuracy for a metric."""
    metric: str
    n_evaluated: int
    mae: float  # Mean Absolute Error
    mape: float  # Mean Absolute Percentage Error (0-1)
    coverage_80: float  # % of actuals within 80% CI
    coverage_95: float  # % of actuals within 95% CI
    bias: float  # Mean signed error (positive = overpredicting)


# ── Constants ───────────────────────────────────────────────────────

MIN_TRAINING_POINTS = 14  # 2 weeks minimum history
DEFAULT_HORIZON = 3
MAX_HORIZON = 7
DEFAULT_ALPHA = 0.3  # Level smoothing (higher = more reactive)
DEFAULT_BETA = 0.1   # Trend smoothing (lower = more stable trend)


# ── Holt's Exponential Smoothing ────────────────────────────────────


def _holt_smooth(
    values: List[float],
    alpha: float = DEFAULT_ALPHA,
    beta: float = DEFAULT_BETA,
) -> Tuple[List[float], List[float], List[float]]:
    """
    Apply Holt's linear exponential smoothing.

    Returns (levels, trends, fitted_values) of same length as input.
    """
    n = len(values)
    levels = [0.0] * n
    trends = [0.0] * n
    fitted = [0.0] * n

    # Initialize: level = first value, trend = average of first few diffs
    levels[0] = values[0]
    if n > 1:
        # Use average of first 3 diffs (or fewer) for initial trend
        diffs = [values[i + 1] - values[i] for i in range(min(3, n - 1))]
        trends[0] = sum(diffs) / len(diffs)
    fitted[0] = values[0]

    for t in range(1, n):
        # Update level
        levels[t] = alpha * values[t] + (1 - alpha) * (levels[t - 1] + trends[t - 1])
        # Update trend
        trends[t] = beta * (levels[t] - levels[t - 1]) + (1 - beta) * trends[t - 1]
        # Fitted value (one-step-ahead forecast made at t-1)
        fitted[t] = levels[t - 1] + trends[t - 1]

    return levels, trends, fitted


def _compute_residuals(
    values: List[float],
    fitted: List[float],
) -> List[float]:
    """Compute residuals (actual - fitted), skipping first point."""
    return [values[i] - fitted[i] for i in range(1, len(values))]


def _prediction_interval(
    residual_std: float,
    steps_ahead: int,
    level: float = 0.80,
) -> float:
    """
    Compute prediction interval half-width.

    For exponential smoothing, the prediction variance grows with
    the forecast horizon. We use a simple linear scaling.
    """
    from scipy.stats import norm
    z = norm.ppf(1 - (1 - level) / 2)
    # Variance increases roughly as sqrt(h) for level models
    return z * residual_std * np.sqrt(steps_ahead)


# ── Main Forecaster ─────────────────────────────────────────────────


class HealthForecaster:
    """
    Generates short-term forecasts for health metrics.

    Uses Holt's exponential smoothing with personal baseline context.
    Designed for noisy, short health time-series.
    """

    def __init__(
        self,
        alpha: float = DEFAULT_ALPHA,
        beta: float = DEFAULT_BETA,
    ):
        self.alpha = alpha
        self.beta = beta

    def forecast(
        self,
        values: List[float],
        dates: List[date],
        metric: str,
        horizon_days: int = DEFAULT_HORIZON,
    ) -> Optional[Forecast]:
        """
        Generate a forecast for the given metric.

        Args:
            values: Historical metric values (chronological order)
            dates: Corresponding dates for each value
            metric: Metric key name
            horizon_days: Days ahead to forecast (1-7)

        Returns:
            Forecast object, or None if insufficient data.
        """
        if len(values) != len(dates):
            raise ValueError("values and dates must have same length")

        if len(values) < MIN_TRAINING_POINTS:
            logger.info(
                f"Insufficient data for {metric}: {len(values)} < {MIN_TRAINING_POINTS}"
            )
            return None

        horizon_days = min(horizon_days, MAX_HORIZON)

        # Fit Holt's model
        levels, trends, fitted = _holt_smooth(values, self.alpha, self.beta)

        # Compute residual statistics for prediction intervals
        residuals = _compute_residuals(values, fitted)
        residual_std = float(np.std(residuals, ddof=1)) if len(residuals) > 1 else 0.0
        training_mae = float(np.mean(np.abs(residuals))) if residuals else 0.0

        # Guard against zero residual std (constant data)
        if residual_std < 1e-10:
            residual_std = 1e-10

        # Generate predictions
        last_level = levels[-1]
        last_trend = trends[-1]
        last_date = dates[-1]

        predictions = []
        for h in range(1, horizon_days + 1):
            target_date = last_date + timedelta(days=h)
            predicted = last_level + h * last_trend

            # Prediction intervals widen with horizon
            hw_80 = _prediction_interval(residual_std, h, level=0.80)
            hw_95 = _prediction_interval(residual_std, h, level=0.95)

            # Confidence decreases with horizon
            confidence = max(0.1, 1.0 - 0.15 * h)

            predictions.append(PredictionPoint(
                target_date=target_date,
                predicted_value=round(predicted, 2),
                ci_80=(round(predicted - hw_80, 2), round(predicted + hw_80, 2)),
                ci_95=(round(predicted - hw_95, 2), round(predicted + hw_95, 2)),
                confidence=round(confidence, 2),
            ))

        return Forecast(
            metric=metric,
            generated_date=last_date,
            predictions=predictions,
            model_type="holt_exponential_smoothing",
            n_training_points=len(values),
            training_mae=round(training_mae, 4),
            features_used=["historical_values", "linear_trend"],
        )

    def forecast_multiple(
        self,
        metric_series: Dict[str, Tuple[List[float], List[date]]],
        horizon_days: int = DEFAULT_HORIZON,
    ) -> Dict[str, Forecast]:
        """
        Forecast multiple metrics at once.

        Args:
            metric_series: Dict mapping metric_key to (values, dates) tuples
            horizon_days: Days ahead to forecast

        Returns:
            Dict mapping metric_key to Forecast (only includes successful forecasts)
        """
        results = {}
        for metric, (values, dates) in metric_series.items():
            forecast = self.forecast(values, dates, metric, horizon_days)
            if forecast is not None:
                results[metric] = forecast
        return results


# ── Accuracy Tracking ───────────────────────────────────────────────


def evaluate_forecast_accuracy(
    predictions: List[PredictionPoint],
    actuals: List[Tuple[date, float]],
) -> Optional[ForecastAccuracy]:
    """
    Evaluate forecast accuracy against actual outcomes.

    Args:
        predictions: The forecast prediction points
        actuals: List of (date, actual_value) pairs

    Returns:
        ForecastAccuracy or None if no matching dates
    """
    actual_map = {d: v for d, v in actuals}

    errors = []
    pct_errors = []
    in_80 = 0
    in_95 = 0
    matched = 0

    for pred in predictions:
        actual = actual_map.get(pred.target_date)
        if actual is None:
            continue

        matched += 1
        error = actual - pred.predicted_value
        errors.append(error)
        if abs(actual) > 1e-10:
            pct_errors.append(abs(error) / abs(actual))

        if pred.ci_80[0] <= actual <= pred.ci_80[1]:
            in_80 += 1
        if pred.ci_95[0] <= actual <= pred.ci_95[1]:
            in_95 += 1

    if matched == 0:
        return None

    metric = predictions[0].target_date.isoformat()  # placeholder

    return ForecastAccuracy(
        metric="",  # caller should set
        n_evaluated=matched,
        mae=round(float(np.mean(np.abs(errors))), 4),
        mape=round(float(np.mean(pct_errors)), 4) if pct_errors else 0.0,
        coverage_80=round(in_80 / matched, 2),
        coverage_95=round(in_95 / matched, 2),
        bias=round(float(np.mean(errors)), 4),
    )
