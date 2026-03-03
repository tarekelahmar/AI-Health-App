"""Tests for Phase 3.1: Personal Response Database (intervention memory)."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.domain.models.intervention_response import InterventionResponse
from app.domain.models.causal_memory import CausalMemory
from app.engine.memory.response_service import (
    PersonalResponseService,
    ResponseHistory,
    ResponsePrediction,
    SimilarResponse,
    SIMILARITY_GROUPS,
    _INTERVENTION_TO_GROUP,
)


# ── Fixtures ──────────────────────────────────────────────────────────


def _make_response(
    intervention_key="magnesium_glycinate",
    verdict="helpful",
    effect_size=0.6,
    confidence=0.8,
    benefit=4,
    start_days_ago=30,
    end_days_ago=16,
):
    """Create a mock InterventionResponse."""
    r = MagicMock(spec=InterventionResponse)
    r.intervention_key = intervention_key
    r.verdict = verdict
    r.overall_effect_size = effect_size
    r.overall_confidence = confidence
    r.user_perceived_benefit = benefit
    r.start_date = datetime.utcnow() - timedelta(days=start_days_ago)
    r.end_date = datetime.utcnow() - timedelta(days=end_days_ago)
    return r


def _make_causal_memory(
    driver_key="magnesium_glycinate",
    metric_key="sleep_duration",
    direction="improves",
    avg_effect_size=0.5,
    confidence=0.7,
    status="confirmed",
):
    m = MagicMock(spec=CausalMemory)
    m.driver_key = driver_key
    m.metric_key = metric_key
    m.direction = direction
    m.avg_effect_size = avg_effect_size
    m.confidence = confidence
    m.status = status
    return m


class TestResponseHistory:
    """Test response history retrieval."""

    def test_no_history_returns_empty(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        service.response_repo.list_for_user.return_value = []

        history = service.get_response_history(1, "magnesium_glycinate")

        assert history.times_tried == 0
        assert history.verdicts == []
        assert history.avg_effect_size is None
        assert history.most_recent_verdict is None

    def test_single_response_history(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        resp = _make_response(verdict="helpful", effect_size=0.6, confidence=0.8)
        service.response_repo.list_for_user.return_value = [resp]

        history = service.get_response_history(1, "magnesium_glycinate")

        assert history.times_tried == 1
        assert history.verdicts == ["helpful"]
        assert history.avg_effect_size == pytest.approx(0.6)
        assert history.most_recent_verdict == "helpful"

    def test_multiple_responses_averaged(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        r1 = _make_response(verdict="helpful", effect_size=0.6, confidence=0.8, benefit=4)
        r2 = _make_response(verdict="helpful", effect_size=0.4, confidence=0.7, benefit=3)
        r3 = _make_response(verdict="not_helpful", effect_size=0.1, confidence=0.6, benefit=2)
        service.response_repo.list_for_user.return_value = [r1, r2, r3]

        history = service.get_response_history(1, "magnesium_glycinate")

        assert history.times_tried == 3
        assert len(history.verdicts) == 3
        assert history.avg_effect_size == pytest.approx((0.6 + 0.4 + 0.1) / 3, abs=0.01)
        assert history.user_perceived_benefit_avg == pytest.approx(3.0, abs=0.01)


class TestSimilarInterventions:
    """Test similar intervention lookup."""

    def test_no_group_returns_empty(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()

        similar = service.get_similar_interventions(1, "unknown_intervention")
        assert similar == []

    def test_finds_similar_in_group(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()

        # When asked for magnesium_threonate, return a response
        def mock_list(user_id, intervention_key, limit=50):
            if intervention_key == "magnesium_threonate":
                return [_make_response(
                    intervention_key="magnesium_threonate",
                    verdict="helpful",
                    effect_size=0.5,
                )]
            return []

        service.response_repo.list_for_user = mock_list

        similar = service.get_similar_interventions(1, "magnesium_glycinate")

        # Should find magnesium_threonate as similar
        keys = [s.intervention_key for s in similar]
        assert "magnesium_threonate" in keys
        assert similar[0].similarity_group == "magnesium"

    def test_excludes_self_from_similar(self):
        """The queried intervention should not appear in its own similar list."""
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        service.response_repo.list_for_user = lambda *a, **kw: []

        similar = service.get_similar_interventions(1, "magnesium_glycinate")
        keys = [s.intervention_key for s in similar]
        assert "magnesium_glycinate" not in keys


class TestSimilarityGroups:
    """Test the similarity group mappings."""

    def test_all_groups_have_members(self):
        for group, members in SIMILARITY_GROUPS.items():
            assert len(members) >= 2, f"Group {group} should have at least 2 members"

    def test_reverse_map_complete(self):
        for group, members in SIMILARITY_GROUPS.items():
            for member in members:
                assert member in _INTERVENTION_TO_GROUP
                assert _INTERVENTION_TO_GROUP[member] == group


class TestPredictResponse:
    """Test response prediction."""

    def test_no_data_returns_no_data(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        service.response_repo.list_for_user.return_value = []
        service.memory_repo = MagicMock()
        service.memory_repo.list_by_user.return_value = []

        pred = service.predict_response(1, "unknown_thing")

        assert pred.predicted_verdict == "no_data"
        assert pred.confidence == 0.0
        assert pred.basis == "no_data"

    def test_direct_history_predicts_helpful(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        r1 = _make_response(verdict="helpful", effect_size=0.6)
        r2 = _make_response(verdict="helpful", effect_size=0.5)
        service.response_repo.list_for_user.return_value = [r1, r2]

        pred = service.predict_response(1, "magnesium_glycinate")

        assert pred.predicted_verdict == "helpful"
        assert pred.basis == "direct_history"
        assert pred.confidence >= 0.5
        assert pred.prior_responses == 2

    def test_direct_history_predicts_not_helpful(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        r1 = _make_response(verdict="not_helpful", effect_size=0.1)
        r2 = _make_response(verdict="not_helpful", effect_size=0.05)
        r3 = _make_response(verdict="not_helpful", effect_size=0.02)
        r4 = _make_response(verdict="unclear", effect_size=0.1)
        service.response_repo.list_for_user.return_value = [r1, r2, r3, r4]

        pred = service.predict_response(1, "magnesium_glycinate")

        assert pred.predicted_verdict == "not_helpful"
        assert pred.basis == "direct_history"

    def test_causal_memory_fallback(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        # Only 1 direct response — not enough for direct_history prediction
        service.response_repo.list_for_user.return_value = [
            _make_response(verdict="helpful")
        ]
        service.memory_repo = MagicMock()
        service.memory_repo.list_by_user.return_value = [
            _make_causal_memory(
                driver_key="magnesium_glycinate",
                direction="improves",
                confidence=0.8,
            )
        ]

        pred = service.predict_response(1, "magnesium_glycinate")

        assert pred.predicted_verdict == "helpful"
        assert pred.basis == "causal_memory"
        assert pred.confidence < 0.8  # Discounted from causal memory

    def test_similar_intervention_fallback(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()

        # No direct responses for magnesium_glycinate
        # But magnesium_threonate was tried
        def mock_list(user_id, intervention_key, limit=50):
            if intervention_key == "magnesium_threonate":
                return [_make_response(
                    intervention_key="magnesium_threonate",
                    verdict="helpful",
                    effect_size=0.5,
                )]
            return []

        service.response_repo.list_for_user = mock_list
        service.memory_repo = MagicMock()
        service.memory_repo.list_by_user.return_value = []

        pred = service.predict_response(1, "magnesium_glycinate")

        assert pred.predicted_verdict == "helpful"
        assert pred.basis == "similar_interventions"
        assert pred.similar_responses >= 1

    def test_deprecated_causal_memory_ignored(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()
        service.response_repo.list_for_user.return_value = []
        service.memory_repo = MagicMock()
        service.memory_repo.list_by_user.return_value = [
            _make_causal_memory(
                driver_key="magnesium_glycinate",
                direction="improves",
                status="deprecated",
            )
        ]

        pred = service.predict_response(1, "magnesium_glycinate")

        # Deprecated memory should be ignored, so no_data
        assert pred.predicted_verdict == "no_data"

    def test_confidence_increases_with_more_history(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()

        # 2 responses
        service.response_repo.list_for_user.return_value = [
            _make_response(verdict="helpful"),
            _make_response(verdict="helpful"),
        ]
        pred_2 = service.predict_response(1, "magnesium_glycinate")

        # 5 responses
        service.response_repo.list_for_user.return_value = [
            _make_response(verdict="helpful") for _ in range(5)
        ]
        pred_5 = service.predict_response(1, "magnesium_glycinate")

        assert pred_5.confidence > pred_2.confidence


class TestRecordResponse:
    """Test recording responses from evaluations."""

    def test_record_creates_response(self):
        db = MagicMock()
        service = PersonalResponseService(db)
        service.response_repo = MagicMock()

        mock_response = _make_response()
        service.response_repo.create.return_value = mock_response

        result = service.record_response_from_evaluation(
            user_id=1,
            intervention_id=10,
            intervention_key="magnesium_glycinate",
            experiment_id=5,
            start_date=datetime(2026, 1, 1),
            end_date=datetime(2026, 1, 15),
            target_metrics={
                "sleep_duration": {"baseline": 410, "outcome": 445, "effect_size": 0.62}
            },
            verdict="helpful",
            overall_effect_size=0.62,
            overall_confidence=0.85,
            adherence_rate=0.9,
            confounders=["travel"],
            evaluation_ids=[1, 2],
        )

        assert service.response_repo.create.called
        call_kwargs = service.response_repo.create.call_args[1]
        assert call_kwargs["intervention_key"] == "magnesium_glycinate"
        assert call_kwargs["verdict"] == "helpful"
        assert call_kwargs["duration_days"] == 14
