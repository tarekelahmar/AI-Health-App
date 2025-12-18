# AI Health Platform - Implementation Roadmap

> A phased approach to building a Personal Health Operating System
>
> **How to use this document**: Work through phases sequentially. Each phase has clear deliverables, acceptance criteria, and code review checkpoints. Use Cursor for implementation; consult Claude for architectural decisions and code reviews at checkpoints.

---

## Current State Assessment

### What's Working
- Core insight loop (OBSERVE → MODEL → INTERVENE → EVALUATE → SYNTHESIZE)
- Governance architecture (claim policies, safety gates, consent enforcement)
- 10 health domains defined
- Basic wearable integration (WHOOP)
- Frontend with consent flow, insights feed, daily check-ins
- Testing infrastructure (pytest + vitest)

### What's Missing for Vision
- Single wearable support (need multi-source)
- No longitudinal memory (insights don't learn from history)
- No cross-domain reasoning (domains are silos)
- No predictive capabilities
- No personal baseline learning
- Limited statistical rigor
- No experiment framework

---

## Phase Overview

```
Phase 1: Data Foundation         (4-6 weeks)  ← YOU ARE HERE
    ↓
Phase 2: Statistical Upgrade     (4-6 weeks)
    ↓
Phase 3: Longitudinal Memory     (3-4 weeks)
    ↓
Phase 4: Cross-Domain Intelligence (4-5 weeks)
    ↓
Phase 5: Predictive Capabilities (4-5 weeks)
    ↓
Phase 6: Experiment Framework    (3-4 weeks)
    ↓
Phase 7+: Advanced Features      (ongoing)
```

---

## Phase 1: Data Foundation

**Goal**: Robust multi-source data ingestion with quality tracking

### 1.1 Unify Metric Registry
**Priority**: HIGH
**Effort**: 2-3 days

**Current Problem**: Two separate metric definitions exist:
- `backend/app/core/metrics.py` - Used by change detection
- `backend/app/domain/metric_registry.py` - Used by loop runner

**Deliverables**:
1. Create single source of truth: `backend/app/domain/metrics/registry.py`
2. Define comprehensive MetricSpec:
```python
@dataclass
class MetricSpec:
    key: str                    # e.g., "sleep_duration"
    domain: str                 # e.g., "sleep"
    display_name: str           # e.g., "Sleep Duration"
    unit: str                   # e.g., "hours"
    valid_range: Tuple[float, float]
    direction: str              # "higher_better" | "lower_better" | "optimal_range"
    optimal_range: Optional[Tuple[float, float]]
    aggregation: str            # "mean" | "sum" | "min" | "max"
    expected_cadence: str       # "daily" | "hourly" | "continuous"
    population_reference: Optional[Dict]  # age/sex stratified norms
```
3. Update all imports across codebase
4. Add metric validation on ingestion

**Acceptance Criteria**:
- [ ] Single registry file with all metrics
- [ ] All existing code uses unified registry
- [ ] Tests pass
- [ ] No duplicate metric definitions

**Claude Review Checkpoint**: After completing, share the new registry structure for review.

---

### 1.2 Add Provider Abstraction Layer
**Priority**: HIGH
**Effort**: 1 week

**Current Problem**: WHOOP is hardcoded; adding new providers requires significant work.

**Deliverables**:
1. Create provider interface:
```python
# backend/app/integrations/base.py
class HealthDataProvider(ABC):
    @abstractmethod
    async def authenticate(self, credentials: Dict) -> AuthToken: ...

    @abstractmethod
    async def fetch_data(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
        metrics: List[str]
    ) -> List[HealthDataPoint]: ...

    @abstractmethod
    def get_supported_metrics(self) -> List[str]: ...

    @abstractmethod
    def get_rate_limits(self) -> RateLimitConfig: ...
```

2. Refactor WHOOP to implement interface
3. Create provider registry with auto-discovery
4. Add provider health monitoring

**File Structure**:
```
backend/app/integrations/
├── __init__.py
├── base.py              # Abstract base class
├── registry.py          # Provider discovery & registration
├── providers/
│   ├── __init__.py
│   ├── whoop.py         # Existing, refactored
│   ├── oura.py          # Stub for future
│   └── apple_health.py  # Stub for future
└── sync/
    ├── __init__.py
    ├── scheduler.py     # Sync scheduling
    └── reconciler.py    # Data deduplication
```

**Acceptance Criteria**:
- [ ] WHOOP works through new abstraction
- [ ] Adding new provider requires only implementing interface
- [ ] Provider health visible in admin/debug
- [ ] Tests cover provider interface contract

---

### 1.3 Data Quality Pipeline
**Priority**: MEDIUM
**Effort**: 3-4 days

**Current Problem**: No systematic data quality tracking; bad data pollutes insights.

**Deliverables**:
1. Create data quality service:
```python
# backend/app/services/data_quality.py
class DataQualityService:
    def assess_point(self, point: HealthDataPoint) -> QualityAssessment:
        """Check single data point for issues."""

    def assess_coverage(
        self,
        user_id: int,
        metric: str,
        window: timedelta
    ) -> CoverageReport:
        """Check data completeness over time window."""

    def detect_anomalies(
        self,
        user_id: int,
        metric: str,
        method: str = "zscore"  # or "iqr", "isolation_forest"
    ) -> List[AnomalyFlag]:
        """Flag statistical outliers for review."""
```

2. Add quality scores to HealthDataPoint model
3. Create quality dashboard endpoint
4. Filter low-quality data from analysis (configurable threshold)

**Quality Dimensions**:
- Completeness: % of expected data points present
- Timeliness: Lag between measurement and ingestion
- Validity: Within valid_range per metric spec
- Consistency: Agreement across overlapping sources
- Uniqueness: No duplicates

**Acceptance Criteria**:
- [ ] Every data point has quality score
- [ ] Coverage report shows gaps clearly
- [ ] Anomalies flagged but not auto-deleted
- [ ] Quality visible in frontend (even if basic)

---

### 1.4 Subjective Data Capture Expansion
**Priority**: MEDIUM
**Effort**: 3-4 days

**Current Problem**: Daily check-ins capture limited signals; no symptom tracking.

**Deliverables**:
1. Expand check-in schema:
```python
# Current: energy, mood, stress, sleep_quality, notes (5 fields)
# Target: Add configurable symptom tracking

class SymptomLog(Base):
    user_id: int
    timestamp: datetime
    symptom_key: str       # e.g., "headache", "bloating", "brain_fog"
    severity: int          # 0-10
    duration_hours: Optional[float]
    triggers: Optional[List[str]]  # User-reported suspected triggers
    notes: Optional[str]
```

2. Create symptom registry (similar to metrics):
```python
SYMPTOM_REGISTRY = {
    "headache": SymptomSpec(category="neurological", body_system="head"),
    "bloating": SymptomSpec(category="digestive", body_system="gi"),
    # ... 50+ symptoms across body systems
}
```

3. Update frontend DailyCheckIn component
4. Add symptom trends to domain narratives

**Acceptance Criteria**:
- [ ] Users can log 10+ common symptoms
- [ ] Severity tracked over time
- [ ] Symptoms appear in relevant domain insights
- [ ] No performance regression on check-in

**Claude Review Checkpoint**: After Phase 1 complete, do full code review before Phase 2.

---

## Phase 2: Statistical Upgrade

**Goal**: Replace basic statistics with rigorous, uncertainty-aware methods

### 2.1 Robust Baseline Estimation
**Priority**: HIGH
**Effort**: 3-4 days

**Current Problem**: Baselines use simple mean/std, sensitive to outliers.

**Deliverables**:
1. Implement robust estimators:
```python
# backend/app/engine/statistics/baseline.py
class RobustBaseline:
    def __init__(self, method: str = "median_mad"):
        self.method = method

    def fit(self, data: np.ndarray) -> BaselineEstimate:
        if self.method == "median_mad":
            center = np.median(data)
            spread = median_abs_deviation(data)
        elif self.method == "trimmed_mean":
            center = trim_mean(data, proportiontocut=0.1)
            spread = trimmed_std(data)
        elif self.method == "huber":
            # Huber M-estimator
            ...

        return BaselineEstimate(
            center=center,
            spread=spread,
            method=self.method,
            n_samples=len(data),
            confidence_interval=self._compute_ci(data)
        )
```

2. Add minimum sample requirements per metric
3. Store baseline with uncertainty bounds
4. Expose baseline info in API response

**Acceptance Criteria**:
- [ ] Outliers don't skew baseline
- [ ] Confidence intervals on all baselines
- [ ] Minimum 14 days data before baseline "stable"
- [ ] Baseline method logged for auditability

---

### 2.2 Bayesian Confidence Framework
**Priority**: HIGH
**Effort**: 1 week

**Current Problem**: Confidence scores are ad-hoc formulas, not calibrated.

**Deliverables**:
1. Replace confidence calculation with Bayesian approach:
```python
# backend/app/engine/statistics/confidence.py
class BayesianConfidence:
    def __init__(self, prior: str = "weakly_informative"):
        self.prior = prior

    def compute(
        self,
        observed_effect: float,
        baseline: BaselineEstimate,
        n_observations: int,
        effect_variance: float
    ) -> ConfidenceResult:
        """
        Returns posterior probability that effect is real,
        with credible interval.
        """
        # Compute posterior
        posterior = self._update_posterior(
            prior=self._get_prior(),
            likelihood=self._compute_likelihood(observed_effect, effect_variance),
            n=n_observations
        )

        return ConfidenceResult(
            probability_real=posterior.prob_positive,
            credible_interval_80=posterior.hdi(0.8),
            credible_interval_95=posterior.hdi(0.95),
            bayes_factor=self._compute_bf(posterior),
            interpretation=self._interpret(posterior)
        )
```

2. Calibration tracking:
```python
class ConfidenceCalibrator:
    """Track whether 80% confidence claims are right 80% of the time."""

    def record_prediction(self, confidence: float, outcome: bool): ...
    def get_calibration_curve(self) -> CalibrationCurve: ...
    def is_well_calibrated(self) -> bool: ...
```

3. Update all insight generation to use new confidence

**Acceptance Criteria**:
- [ ] All insights have Bayesian confidence
- [ ] Credible intervals replace point estimates
- [ ] Calibration tracked (even if not displayed yet)
- [ ] "Low confidence" insights clearly marked

---

### 2.3 Change Point Detection
**Priority**: MEDIUM
**Effort**: 3-4 days

**Current Problem**: Trend detection uses rolling windows; misses sudden shifts.

**Deliverables**:
1. Implement PELT algorithm for change point detection:
```python
# backend/app/engine/detectors/change_point.py
class ChangePointDetector:
    def __init__(self, method: str = "pelt", min_segment: int = 7):
        self.method = method
        self.min_segment = min_segment

    def detect(self, series: pd.Series) -> List[ChangePoint]:
        if self.method == "pelt":
            # Pruned Exact Linear Time
            algo = rpt.Pelt(model="rbf", min_size=self.min_segment)
            result = algo.fit_predict(series.values, pen=10)
        elif self.method == "bocpd":
            # Bayesian Online Change Point Detection
            ...

        return [
            ChangePoint(
                index=idx,
                timestamp=series.index[idx],
                confidence=self._compute_confidence(idx, series),
                magnitude=self._compute_magnitude(idx, series),
                direction="increase" if ... else "decrease"
            )
            for idx in result
        ]
```

2. Integrate into insight loop
3. Create "regime" concept (periods between change points)
4. Display change points in frontend charts

**Acceptance Criteria**:
- [ ] Change points detected with < 3 day lag
- [ ] False positive rate < 10%
- [ ] Magnitude and direction captured
- [ ] Visible on metric charts

---

### 2.4 Multiple Testing Correction
**Priority**: MEDIUM
**Effort**: 2-3 days

**Current Problem**: Running many correlations inflates false discoveries.

**Deliverables**:
1. Implement FDR control:
```python
# backend/app/engine/statistics/multiple_testing.py
class FDRController:
    def __init__(self, method: str = "benjamini_hochberg", alpha: float = 0.1):
        self.method = method
        self.alpha = alpha  # Target FDR

    def adjust(self, p_values: List[float]) -> AdjustedResults:
        if self.method == "benjamini_hochberg":
            rejected, adjusted_p, _, _ = multipletests(
                p_values, alpha=self.alpha, method='fdr_bh'
            )

        return AdjustedResults(
            original_p=p_values,
            adjusted_p=adjusted_p,
            rejected=rejected,
            n_discoveries=sum(rejected),
            expected_false_discoveries=sum(rejected) * self.alpha
        )
```

2. Apply to all correlation/attribution analyses
3. Log adjustment in insight metadata
4. Surface "adjusted significance" in UI

**Acceptance Criteria**:
- [ ] All multi-comparison analyses use FDR
- [ ] Expected false discovery rate ≤ 10%
- [ ] Adjustment method logged
- [ ] Fewer spurious correlations surfaced

**Claude Review Checkpoint**: After Phase 2 complete, review statistical implementations.

---

## Phase 3: Longitudinal Memory

**Goal**: System remembers and learns from user's history

### 3.1 Personal Response Database
**Priority**: HIGH
**Effort**: 1 week

**Current Problem**: System doesn't remember what worked for this user before.

**Deliverables**:
1. Create intervention response tracking:
```python
# backend/app/domain/models/intervention_response.py
class InterventionResponse(Base):
    id: int
    user_id: int
    intervention_key: str      # e.g., "magnesium_glycinate"
    start_date: date
    end_date: Optional[date]

    # Outcome tracking
    target_metrics: List[str]  # What we hoped to improve
    baseline_values: Dict[str, float]
    outcome_values: Dict[str, float]
    effect_sizes: Dict[str, float]

    # Statistical assessment
    confidence: float
    verdict: str               # "helpful" | "not_helpful" | "unclear"
    confounders_noted: List[str]

    # User feedback
    user_perceived_benefit: Optional[int]  # 1-5
    user_notes: Optional[str]
    would_recommend: Optional[bool]
```

2. Create response query service:
```python
class PersonalResponseService:
    def get_response_history(
        self,
        user_id: int,
        intervention: str
    ) -> List[InterventionResponse]:
        """What happened when this user tried this before?"""

    def get_similar_interventions(
        self,
        user_id: int,
        intervention: str
    ) -> List[SimilarResponse]:
        """What about similar interventions?"""

    def predict_response(
        self,
        user_id: int,
        intervention: str
    ) -> ResponsePrediction:
        """Based on history, how likely to help?"""
```

3. Integrate into insight generation
4. Display history when suggesting interventions

**Acceptance Criteria**:
- [ ] Every intervention outcome recorded
- [ ] Historical verdicts queryable
- [ ] "You tried this before" shown in UI
- [ ] Predictions improve with history

---

### 3.2 Pattern Library
**Priority**: MEDIUM
**Effort**: 4-5 days

**Current Problem**: System rediscovers the same patterns repeatedly.

**Deliverables**:
1. Create personal pattern storage:
```python
# backend/app/domain/models/pattern.py
class PersonalPattern(Base):
    id: int
    user_id: int
    pattern_type: str          # "correlation" | "trigger" | "cycle" | "response"

    # Pattern definition
    input_signals: List[str]   # What predicts
    output_signal: str         # What is predicted
    relationship: Dict         # Statistical details

    # Confidence tracking
    times_observed: int
    times_confirmed: int
    current_confidence: float

    # Temporal aspects
    first_detected: datetime
    last_confirmed: datetime
    typical_lag_hours: Optional[float]

    # Status
    status: str                # "hypothesis" | "confirmed" | "disproven"
    user_acknowledged: bool
```

2. Pattern lifecycle management:
```python
class PatternManager:
    def detect_new_pattern(self, user_id: int, data: Dict) -> Optional[Pattern]: ...
    def confirm_pattern(self, pattern_id: int, observation: Dict): ...
    def invalidate_pattern(self, pattern_id: int, reason: str): ...
    def get_active_patterns(self, user_id: int) -> List[Pattern]: ...
```

3. Use patterns in future insight generation
4. Display "Your patterns" section in UI

**Acceptance Criteria**:
- [ ] Patterns stored with confidence
- [ ] Patterns updated with new observations
- [ ] Old patterns can be invalidated
- [ ] Patterns inform future insights

---

### 3.3 Regime Detection
**Priority**: MEDIUM
**Effort**: 3-4 days

**Current Problem**: System doesn't recognize "sick", "traveling", "stressed" states.

**Deliverables**:
1. Create regime classifier:
```python
# backend/app/engine/regime/classifier.py
class RegimeClassifier:
    REGIMES = [
        "normal",
        "illness",
        "travel",
        "high_stress",
        "recovery",
        "training_peak",
        "menstrual_phase",  # If applicable
    ]

    def classify(
        self,
        user_id: int,
        date: date,
        features: Dict[str, float]
    ) -> RegimeClassification:
        """Determine what regime user is in."""

    def get_regime_history(
        self,
        user_id: int,
        window: timedelta
    ) -> List[RegimePeriod]:
        """Return regime timeline."""
```

2. Adjust baselines per regime
3. Suppress insights during abnormal regimes
4. Show regime context in insights

**Acceptance Criteria**:
- [ ] At least 4 regimes detected
- [ ] Regime shown on timeline
- [ ] Insights acknowledge regime context
- [ ] User can manually mark regime

**Claude Review Checkpoint**: After Phase 3 complete, review memory architecture.

---

## Phase 4: Cross-Domain Intelligence

**Goal**: Understand how health domains interact

### 4.1 Domain Dependency Graph
**Priority**: HIGH
**Effort**: 1 week

**Current Problem**: Domains analyzed in isolation; cascades missed.

**Deliverables**:
1. Define causal relationships between domains:
```python
# backend/app/domain/causal_graph.py
DOMAIN_GRAPH = {
    "sleep": {
        "affects": ["energy", "cognitive", "stress", "immune"],
        "affected_by": ["stress", "cardiometabolic"],
        "typical_lag_days": {"energy": 0, "cognitive": 0, "immune": 2}
    },
    "stress": {
        "affects": ["sleep", "gi", "immune", "hormonal"],
        "affected_by": ["sleep", "external_events"],
        "typical_lag_days": {"sleep": 0, "gi": 1, "immune": 3}
    },
    # ... all 10 domains
}
```

2. Create cascade detector:
```python
class CascadeDetector:
    def detect_cascade(
        self,
        user_id: int,
        trigger_domain: str,
        trigger_event: Dict
    ) -> List[CascadeStep]:
        """Predict downstream effects of a domain change."""

    def explain_cascade(
        self,
        user_id: int,
        observed_changes: List[DomainChange]
    ) -> CascadeExplanation:
        """Given multi-domain changes, find root cause."""
```

3. Integrate cascade context into insights
4. Visualize domain connections in UI

**Acceptance Criteria**:
- [ ] Domain relationships defined
- [ ] Cascades detected within 48 hours
- [ ] Root cause hypotheses generated
- [ ] Domain graph visible in UI

---

### 4.2 Cross-Domain Correlation Engine
**Priority**: MEDIUM
**Effort**: 4-5 days

**Current Problem**: Correlations only within-domain; miss sleep→stress links.

**Deliverables**:
1. Create cross-domain analyzer:
```python
# backend/app/engine/attribution/cross_domain.py
class CrossDomainAnalyzer:
    def find_correlations(
        self,
        user_id: int,
        source_domain: str,
        target_domain: str,
        min_confidence: float = 0.7
    ) -> List[CrossDomainCorrelation]:
        """Find relationships between domains."""

    def test_causal_hypothesis(
        self,
        user_id: int,
        cause_metric: str,
        effect_metric: str,
        expected_lag: timedelta
    ) -> CausalTestResult:
        """Granger causality test with lag."""
```

2. Time-lagged correlation support
3. Confound adjustment (age, season, etc.)
4. Display cross-domain insights

**Acceptance Criteria**:
- [ ] Cross-domain correlations found
- [ ] Lag relationships captured
- [ ] Confounders adjusted
- [ ] Cross-domain insights surfaced

---

### 4.3 Unified Health Score (Optional)
**Priority**: LOW
**Effort**: 3-4 days

**Note**: Controversial - may oversimplify. Consider carefully.

**Deliverables**:
1. If implemented, create composite score:
```python
class UnifiedHealthScore:
    def compute(
        self,
        user_id: int,
        date: date
    ) -> HealthScoreResult:
        domain_scores = self._compute_domain_scores(user_id, date)

        # Weighted combination, weights learned from user's priorities
        weights = self._get_user_weights(user_id)
        composite = sum(w * s for w, s in zip(weights, domain_scores))

        return HealthScoreResult(
            overall=composite,
            by_domain=domain_scores,
            trend="improving" | "stable" | "declining",
            main_contributors=self._find_contributors(domain_scores)
        )
```

2. Make it opt-in, not default
3. Always show breakdown, never just number
4. Explain methodology transparently

**Claude Review Checkpoint**: After Phase 4 complete, review cross-domain logic.

---

## Phase 5: Predictive Capabilities

**Goal**: Anticipate health changes before they happen

### 5.1 Short-Term Forecasting
**Priority**: HIGH
**Effort**: 1 week

**Deliverables**:
1. Create forecasting engine:
```python
# backend/app/engine/forecasting/predictor.py
class HealthForecaster:
    def forecast(
        self,
        user_id: int,
        metric: str,
        horizon_days: int = 3
    ) -> Forecast:
        # Use personal historical patterns + recent trajectory
        model = self._get_model(user_id, metric)
        predictions = model.predict(horizon_days)

        return Forecast(
            metric=metric,
            predictions=[
                PredictionPoint(
                    date=d,
                    predicted_value=v,
                    confidence_interval=(lo, hi),
                    confidence=c
                )
                for d, v, (lo, hi), c in predictions
            ],
            model_type=model.type,
            features_used=model.features
        )
```

2. Key forecasts:
   - Tomorrow's HRV
   - Tomorrow's energy level
   - Sleep quality tonight
   - Recovery time after stress event

3. Track forecast accuracy
4. Display forecasts in morning brief

**Acceptance Criteria**:
- [ ] 3-day forecasts for key metrics
- [ ] Confidence intervals on predictions
- [ ] Forecast accuracy tracked
- [ ] Forecasts visible in UI

---

### 5.2 Risk Window Detection
**Priority**: MEDIUM
**Effort**: 4-5 days

**Deliverables**:
1. Create risk detector:
```python
class RiskWindowDetector:
    def detect_vulnerability(
        self,
        user_id: int,
        risk_type: str  # "illness", "burnout", "injury"
    ) -> RiskAssessment:
        features = self._extract_risk_features(user_id)

        # Check against personal thresholds
        risk_score = self._compute_risk(features, risk_type)

        return RiskAssessment(
            risk_type=risk_type,
            risk_level="low" | "moderate" | "elevated" | "high",
            risk_score=risk_score,
            contributing_factors=self._identify_factors(features),
            recommended_actions=self._get_recommendations(risk_type, risk_score)
        )
```

2. Risk types to detect:
   - Illness vulnerability (immune suppression signals)
   - Burnout trajectory
   - Overtraining risk
   - Sleep debt accumulation

3. Proactive alerts when risk elevated
4. Show risk factors and mitigation

**Acceptance Criteria**:
- [ ] At least 3 risk types detected
- [ ] Alerts before, not after, problems
- [ ] Contributing factors explained
- [ ] Actionable recommendations

---

### 5.3 Recovery Time Estimation
**Priority**: LOW
**Effort**: 3-4 days

**Deliverables**:
1. Create recovery estimator:
```python
class RecoveryEstimator:
    def estimate_recovery(
        self,
        user_id: int,
        current_state: Dict[str, float],
        target_baseline: bool = True
    ) -> RecoveryEstimate:
        # Use personal recovery patterns
        historical_recoveries = self._get_recovery_history(user_id)

        return RecoveryEstimate(
            estimated_days=days,
            confidence_interval=(lo, hi),
            factors_affecting_recovery=factors,
            acceleration_opportunities=opportunities
        )
```

2. Track recovery accuracy
3. Learn personal recovery rates
4. Show recovery trajectory in UI

**Claude Review Checkpoint**: After Phase 5 complete, review predictive models.

---

## Phase 6: Experiment Framework

**Goal**: Enable rigorous self-experimentation

### 6.1 Experiment Design Engine
**Priority**: HIGH
**Effort**: 1 week

**Deliverables**:
1. Create experiment designer:
```python
# backend/app/engine/experiments/designer.py
class ExperimentDesigner:
    def design(
        self,
        user_id: int,
        hypothesis: str,
        intervention: str,
        target_metrics: List[str]
    ) -> ExperimentDesign:
        # Calculate required duration
        baseline_variance = self._get_variance(user_id, target_metrics)
        min_detectable_effect = 0.3  # Cohen's d
        required_days = self._power_analysis(baseline_variance, min_detectable_effect)

        return ExperimentDesign(
            hypothesis=hypothesis,
            intervention=intervention,
            target_metrics=target_metrics,

            # Timeline
            baseline_days=14,
            intervention_days=required_days,
            washout_days=7,  # If applicable

            # Success criteria (pre-registered)
            primary_metric=target_metrics[0],
            success_threshold=min_detectable_effect,
            required_confidence=0.8,

            # Adherence requirements
            min_adherence=0.8,
            tracking_requirements=["daily_checkin", "intervention_log"]
        )
```

2. Experiment lifecycle:
   - Design → Baseline → Intervention → Washout → Analysis → Verdict

3. Pre-registration of success criteria
4. Adherence tracking
5. Automated analysis at completion

**Acceptance Criteria**:
- [ ] Power analysis for duration
- [ ] Pre-registered success criteria
- [ ] Adherence tracked
- [ ] Automated verdict generation

---

### 6.2 Experiment Execution & Tracking
**Priority**: MEDIUM
**Effort**: 4-5 days

**Deliverables**:
1. Create experiment tracker:
```python
class ExperimentTracker:
    def start_experiment(
        self,
        user_id: int,
        design: ExperimentDesign
    ) -> ActiveExperiment: ...

    def log_adherence(
        self,
        experiment_id: int,
        date: date,
        adhered: bool,
        notes: Optional[str]
    ): ...

    def get_progress(
        self,
        experiment_id: int
    ) -> ExperimentProgress:
        """Current phase, days remaining, adherence rate, etc."""

    def analyze(
        self,
        experiment_id: int
    ) -> ExperimentResult:
        """Run analysis when complete."""
```

2. Daily reminders during experiments
3. Progress visualization
4. Early stopping rules (if clearly working/not working)

**Acceptance Criteria**:
- [ ] Experiments tracked end-to-end
- [ ] Adherence visible
- [ ] Early stopping available
- [ ] Results stored in response database

---

### 6.3 Experiment UI
**Priority**: MEDIUM
**Effort**: 3-4 days

**Deliverables**:
1. Experiment dashboard page
2. Design wizard (guided setup)
3. Progress tracker with charts
4. Results summary with interpretation

**Claude Review Checkpoint**: After Phase 6 complete, full system review.

---

## Phase 7+: Advanced Features (Future)

These are north star features, not immediate priorities:

### 7.1 Multi-User Learning (Privacy-Preserving)
- Federated learning from aggregate patterns
- "People like you" insights
- Population reference data

### 7.2 Clinician Interface
- Structured summaries for doctor visits
- Exportable reports
- Shareable trend visualizations

### 7.3 Advanced Data Sources
- Continuous glucose monitors
- Blood pressure monitors
- Genetic data integration
- Lab result import

### 7.4 Natural Language Interface
- Ask questions about your health
- Voice check-ins
- Conversational insights

### 7.5 Biological Age Tracking
- Epigenetic clock integration
- Biological vs chronological age
- Age acceleration/deceleration trends

---

## Code Review Protocol

When using Cursor for implementation, checkpoint with Claude for:

### After Each Phase
1. **Architecture Review**: Is the structure maintainable?
2. **Safety Audit**: Any governance bypasses or safety gaps?
3. **Test Coverage**: Are critical paths covered?
4. **Performance Check**: Any obvious bottlenecks?

### What to Share for Review
```
- New/modified file paths
- Key design decisions made
- Any deviations from plan
- Test results
- Questions or concerns
```

### Review Request Template
```
Phase: [X]
Completed: [list of deliverables]
Files changed: [list]
Design decisions: [explain any choices]
Tests passing: [yes/no, details]
Questions: [specific questions]
```

---

## Success Metrics by Phase

| Phase | Key Metrics |
|-------|-------------|
| 1 | 100% metric coverage, data quality >90% |
| 2 | Confidence calibration within 10% |
| 3 | 80% pattern recall, regime detection >85% accurate |
| 4 | Cross-domain cascades detected within 48h |
| 5 | Forecast accuracy >70% for 1-day predictions |
| 6 | Experiment completion rate >60%, verdict accuracy >80% |

---

## Appendix: Key Files Reference

### Backend Core
```
backend/app/engine/
├── loop_runner.py          # Main insight loop
├── governance/             # Claim policies, suppression
├── guardrails/             # Safety gates
├── detectors/              # Change, trend, instability
├── attribution/            # Signal correlation
├── statistics/             # (New) Statistical methods
├── forecasting/            # (New) Predictive models
└── experiments/            # (New) Experiment framework
```

### Frontend Core
```
frontend/src/
├── pages/
│   ├── InsightsFeedPage.tsx   # Main insights view
│   ├── ConsentPage.tsx        # Consent flow
│   └── Dashboard.tsx          # Overview
├── components/
│   ├── SafetyBadge.tsx        # Governance UI
│   ├── ConfidenceBar.tsx      # Uncertainty display
│   └── DailyCheckIn.tsx       # Subjective data
└── api/
    └── client.ts              # Unified API client
```

---

*Last updated: December 2024*
*Version: 1.0*
