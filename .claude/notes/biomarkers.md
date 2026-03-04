# Biomarkers & Functional Medicine Track

> Last verified: 2026-03-04

## Architecture

```
Wearable Providers (WHOOP, Oura, Apple Health)
    |
    v
Provider Abstraction Layer (integrations/providers/)
    |
    v
Normalized HealthDataPoints (metric_type, value, unit, timestamp, source)
    |
    +---> Baseline Service: robust estimation (median, MAD)
    |
    +---> Detectors:
    |       Change Detector (z-score based)
    |       Trend Detector (slope-based)
    |       Instability Detector (variability ratio)
    |       Change Point Detector (PELT algorithm)
    |
    +---> Statistics:
    |       Bayesian confidence scoring
    |       FDR correction for multiple testing
    |
    +---> Advanced Analysis:
    |       Cross-signal attribution
    |       Cross-domain correlation
    |       Cascade detection
    |       Forecasting & risk detection
    |
    v
Insights -> Governance Pipeline -> User
```

## Key Files

### Backend - Data Ingestion
| File | Purpose |
|------|---------|
| `app/providers/whoop/whoop_client.py` | WHOOP API client |
| `app/providers/whoop/whoop_adapter.py` | WHOOP data normalization |
| `app/providers/whoop/whoop_oauth.py` | WHOOP OAuth flow |
| `app/integrations/providers/whoop_provider.py` | Provider abstraction for WHOOP |
| `app/integrations/providers/oura_provider.py` | Provider abstraction for Oura |
| `app/integrations/providers/apple_health_provider.py` | Provider abstraction for Apple Health |
| `app/engine/providers/provider_sync_service.py` | Sync orchestration |
| `app/domain/models/health_data_point.py` | Universal data schema |
| `app/domain/metrics/registry.py` | Metric definitions (MetricSpec) |

### Backend - Detection & Statistics
| File | Purpose |
|------|---------|
| `app/engine/detectors/change_detector.py` | Z-score based change detection |
| `app/engine/detectors/trend_detector.py` | Slope-based trend detection |
| `app/engine/detectors/instability_detector.py` | Variability detection |
| `app/engine/detectors/change_point_detector.py` | PELT-based structural shifts |
| `app/engine/statistics/baseline.py` | Baseline estimation |
| `app/engine/statistics/robust_baseline.py` | Median/MAD baselines |
| `app/engine/statistics/confidence.py` | Bayesian confidence scoring |
| `app/engine/statistics/multiple_testing.py` | FDR correction |
| `app/engine/baseline_service.py` | Baseline management |

### Backend - Advanced Analysis
| File | Purpose |
|------|---------|
| `app/engine/attribution/cross_signal_engine.py` | Cross-signal causal attribution |
| `app/engine/reasoning/cross_domain_correlator.py` | Cross-domain reasoning |
| `app/engine/reasoning/cascade_detector.py` | Cascade effect detection |
| `app/engine/forecasting/predictor.py` | Prediction models |
| `app/engine/forecasting/risk_detector.py` | Risk identification |

### Frontend
| File | Purpose |
|------|---------|
| `src/pages/DashboardPage.tsx` | Main dashboard |
| `src/pages/DomainsPage.tsx` | Health domains overview |
| `src/pages/DomainDetailPage.tsx` | Individual domain detail |
| `src/pages/ForecastsPage.tsx` | Predictions view |
| `src/components/dashboard/MetricSparklineRow.tsx` | Metric sparklines |
| `src/components/dashboard/RiskOverview.tsx` | Risk overview display |
| `src/components/dashboard/RiskAlertCard.tsx` | Risk alert cards |
| `src/components/dashboard/ActiveExperimentCard.tsx` | Active experiment display |
| `src/components/dashboard/RecentInsightsCard.tsx` | Recent insights |
| `src/components/dashboard/RegimeBanner.tsx` | Regime status banner |

### Tests
- `tests/unit/engine/test_robust_baseline.py`
- `tests/unit/engine/test_bayesian_confidence.py`
- `tests/unit/engine/test_change_point_detector.py`
- `tests/unit/engine/test_fdr_correction.py`
- `tests/unit/engine/test_cross_domain_correlator.py`
- `tests/unit/engine/test_forecaster.py`
- `tests/unit/engine/test_risk_detector.py`

## Shared Dependencies (touch carefully)

- `app/engine/loop_runner.py` -- Orchestrates all detectors
- `app/engine/insight_factory.py` -- Creates insight payloads
- `app/engine/governance/` -- All insights must pass governance
- `app/domain/health_domains.py` -- Domain definitions

## Conventions

### Metric Registry (MetricSpec)
| Field | Description |
|-------|-------------|
| `key` | Snake_case identifier (e.g., `sleep_duration`) |
| `domain` | Health domain enum value |
| `display_name` | Human-readable (e.g., "Sleep Duration") |
| `unit` | Display unit (e.g., "min", "ms", "bpm") |
| `valid_range` | Tuple of (min, max) |
| `direction` | `higher_better`, `lower_better`, or `optimal_range` |
| `expected_cadence` | `daily`, `hourly`, or `continuous` |

### Current Provider: WHOOP
Metrics: sleep_duration, sleep_efficiency, hrv_rmssd, resting_heart_rate, respiratory_rate, recovery_score, strain_score, skin_temp_deviation, spo2

## Lessons Learned
<!-- After corrections or non-obvious discoveries, add entries here. -->
<!-- Format: - **YYYY-MM-DD**: Lesson. Context: what triggered it. -->
