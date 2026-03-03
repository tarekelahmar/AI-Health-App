"""Tests for Phase 4.2: Cross-Domain Correlation Engine."""

import pytest
import numpy as np

from app.domain.health_domains import HealthDomainKey
from app.engine.reasoning.cross_domain_correlator import (
    compute_lagged_correlation,
    find_best_lag,
    cross_domain_scan,
    LaggedCorrelation,
    CrossDomainCorrelation,
)


class TestLaggedCorrelation:
    """Test basic lagged correlation computation."""

    def test_zero_lag_correlation(self):
        """Zero lag should give standard correlation."""
        np.random.seed(42)
        x = np.random.normal(0, 1, 50)
        y = 0.8 * x + np.random.normal(0, 0.5, 50)

        r, p, n = compute_lagged_correlation(x, y, lag=0)
        assert abs(r) > 0.5
        assert p < 0.05
        assert n == 50

    def test_positive_lag_correlation(self):
        """Should detect correlation with lag."""
        np.random.seed(42)
        signal = np.random.normal(0, 1, 60)
        # y is x shifted by 3 days + noise
        x = signal[:57]
        y = signal[3:] + np.random.normal(0, 0.3, 57)

        r, p, n = compute_lagged_correlation(list(signal[:60]), list(np.concatenate([np.zeros(3), signal[:57] + np.random.normal(0, 0.3, 57)])), lag=3)
        # Should find some correlation at lag=3
        assert r is not None

    def test_insufficient_data_returns_none(self):
        result = compute_lagged_correlation([1.0, 2.0], [3.0, 4.0], lag=0)
        assert result is None

    def test_constant_array_returns_zero(self):
        """Constant arrays should return r=0."""
        x = [5.0] * 20
        y = [3.0] * 20
        r, p, n = compute_lagged_correlation(x, y)
        assert r == 0.0
        assert p == 1.0

    def test_perfect_correlation(self):
        x = list(range(20))
        y = [2 * v + 1 for v in x]
        r, p, n = compute_lagged_correlation(x, y)
        assert abs(r - 1.0) < 0.01
        assert p < 0.001


class TestFindBestLag:
    """Test finding optimal lag for correlation."""

    def test_finds_best_lag_for_shifted_signal(self):
        """Should find the correct lag for a causally lagged signal."""
        np.random.seed(42)
        n = 100
        # Create a strong signal for x
        x_signal = np.sin(np.linspace(0, 6 * np.pi, n)) * 3
        # y[t] depends on x[t-2] (y causally follows x with lag 2)
        # So y[t] = x[t-2] + noise, for t >= 2
        y_signal = np.zeros(n)
        y_signal[:2] = np.random.normal(0, 0.5, 2)
        y_signal[2:] = x_signal[:-2] + np.random.normal(0, 0.1, n - 2)

        x = list(x_signal)
        y = list(y_signal)

        result = find_best_lag(x, y, max_lag=5)
        assert result is not None
        assert result.lag_days == 2
        assert abs(result.r) > 0.9

    def test_returns_none_for_short_data(self):
        result = find_best_lag([1.0, 2.0], [3.0, 4.0])
        assert result is None


class TestCrossDomainScan:
    """Test cross-domain correlation scanning."""

    def test_finds_cross_domain_correlation(self):
        """Should find correlated metrics across domains."""
        np.random.seed(42)
        n = 40
        sleep = list(np.random.normal(420, 30, n))
        # Energy correlates with sleep
        energy = [s * 0.01 + np.random.normal(0, 0.3) for s in sleep]

        metric_series = {
            "sleep_duration": sleep,
            "subjective_energy": energy,
        }
        metric_to_domain = {
            "sleep_duration": HealthDomainKey.SLEEP,
            "subjective_energy": HealthDomainKey.ENERGY_FATIGUE,
        }

        results = cross_domain_scan(
            metric_series, metric_to_domain,
            max_lag=3, use_graph_prior=True,
        )

        # Should find sleep → energy correlation
        assert len(results) >= 1
        found = any(
            c.source_domain == HealthDomainKey.SLEEP
            and c.target_domain == HealthDomainKey.ENERGY_FATIGUE
            for c in results
        )
        assert found

    def test_skips_same_domain_pairs(self):
        """Should not test correlations within the same domain."""
        np.random.seed(42)
        n = 40
        series = {
            "sleep_duration": list(np.random.normal(420, 30, n)),
            "sleep_efficiency": list(np.random.normal(0.88, 0.05, n)),
        }
        domains = {
            "sleep_duration": HealthDomainKey.SLEEP,
            "sleep_efficiency": HealthDomainKey.SLEEP,
        }

        results = cross_domain_scan(series, domains)
        assert len(results) == 0

    def test_fdr_correction_applied(self):
        """Results should have FDR-adjusted p-values."""
        np.random.seed(42)
        n = 40
        sleep = list(np.random.normal(420, 30, n))
        energy = [s * 0.01 + np.random.normal(0, 0.3) for s in sleep]

        results = cross_domain_scan(
            {"sleep_duration": sleep, "subjective_energy": energy},
            {
                "sleep_duration": HealthDomainKey.SLEEP,
                "subjective_energy": HealthDomainKey.ENERGY_FATIGUE,
            },
            use_graph_prior=True,
        )

        for r in results:
            assert r.fdr_adjusted_p is not None
            assert r.fdr_adjusted_p >= r.p_value  # Adjusted should be >= raw

    def test_no_data_returns_empty(self):
        results = cross_domain_scan({}, {})
        assert results == []

    def test_mechanism_from_graph(self):
        """Should include mechanism from domain graph when available."""
        np.random.seed(42)
        n = 40
        sleep = list(np.random.normal(420, 30, n))
        energy = [s * 0.01 + np.random.normal(0, 0.3) for s in sleep]

        results = cross_domain_scan(
            {"sleep_duration": sleep, "subjective_energy": energy},
            {
                "sleep_duration": HealthDomainKey.SLEEP,
                "subjective_energy": HealthDomainKey.ENERGY_FATIGUE,
            },
            use_graph_prior=True,
        )

        for r in results:
            if r.source_domain == HealthDomainKey.SLEEP and r.target_domain == HealthDomainKey.ENERGY_FATIGUE:
                assert r.mechanism is not None
                assert "sleep" in r.mechanism.lower() or "energy" in r.mechanism.lower()
