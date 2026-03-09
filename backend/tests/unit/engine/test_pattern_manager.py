"""Tests for Phase 3.2: Pattern Library and Pattern Manager."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.domain.models.personal_pattern import PersonalPattern
from app.engine.memory.pattern_manager import (
    PatternManager,
    PatternDetection,
    CONFIRM_CONFIDENCE,
    CONFIRM_MIN_OBSERVATIONS,
    DISPROVE_CONFIDENCE,
    CONFIRM_RATE,
    CONTRADICT_RATE,
)


def _make_pattern(
    pattern_id=1,
    pattern_type="correlation",
    input_signals=None,
    output_signal="hrv_rmssd",
    status="hypothesis",
    confidence=0.3,
    times_observed=1,
    times_confirmed=0,
):
    p = MagicMock(spec=PersonalPattern)
    p.id = pattern_id
    p.user_id = 1
    p.pattern_type = pattern_type
    p.input_signals_json = input_signals or ["late_caffeine"]
    p.output_signal = output_signal
    p.status = status
    p.current_confidence = confidence
    p.times_observed = times_observed
    p.times_confirmed = times_confirmed
    p.relationship_json = {"direction": "negative"}
    p.first_detected = datetime(2026, 1, 1)
    p.last_confirmed = None
    return p


class TestPatternDetection:
    """Test detecting new patterns."""

    def test_creates_new_pattern(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()
        manager.repo.find_matching.return_value = None

        new_pattern = _make_pattern(confidence=0.3)
        manager.repo.create.return_value = new_pattern

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            relationship={"direction": "negative", "r": -0.65},
        )

        assert result.action == "created"
        assert result.new_confidence == 0.3
        assert result.previous_confidence is None
        assert result.status_changed is False
        manager.repo.create.assert_called_once()

    def test_updates_existing_pattern_on_confirm(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        existing = _make_pattern(confidence=0.5, times_confirmed=1)
        manager.repo.find_matching.return_value = existing
        manager.repo.get_by_id.return_value = existing

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            confirmed=True,
        )

        assert result.action == "confirmed"
        assert result.previous_confidence == 0.5
        expected_new = 0.5 + (1 - 0.5) * CONFIRM_RATE
        assert result.new_confidence == pytest.approx(expected_new, abs=0.01)

    def test_updates_existing_pattern_on_contradict(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        existing = _make_pattern(confidence=0.5, times_confirmed=1)
        manager.repo.find_matching.return_value = existing
        manager.repo.get_by_id.return_value = existing

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            confirmed=False,
        )

        assert result.action == "contradicted"
        expected_new = 0.5 - 0.5 * CONTRADICT_RATE
        assert result.new_confidence == pytest.approx(expected_new, abs=0.01)


class TestPatternLifecycle:
    """Test hypothesis → confirmed → disproven lifecycle."""

    def test_promotes_to_confirmed(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        # Pattern at high confidence with enough confirmations
        existing = _make_pattern(
            confidence=0.65,
            times_confirmed=CONFIRM_MIN_OBSERVATIONS - 1,
            status="hypothesis",
        )
        manager.repo.find_matching.return_value = existing
        manager.repo.get_by_id.return_value = existing

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            confirmed=True,
        )

        # New confidence should cross threshold
        expected = 0.65 + (1 - 0.65) * CONFIRM_RATE
        assert expected >= CONFIRM_CONFIDENCE
        assert result.status_changed is True
        manager.repo.update_status.assert_called_with(existing.id, "confirmed")

    def test_disproves_low_confidence(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        # Pattern at very low confidence
        existing = _make_pattern(
            confidence=0.1,
            times_confirmed=0,
            status="hypothesis",
        )
        manager.repo.find_matching.return_value = existing
        manager.repo.get_by_id.return_value = existing

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            confirmed=False,
        )

        # Confidence should drop below disprove threshold
        expected = 0.1 - 0.1 * CONTRADICT_RATE
        assert expected < DISPROVE_CONFIDENCE
        assert result.status_changed is True
        manager.repo.update_status.assert_called_with(existing.id, "disproven")

    def test_confidence_bounded_0_1(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        # Very high confidence
        existing = _make_pattern(confidence=0.99, times_confirmed=10, status="confirmed")
        manager.repo.find_matching.return_value = existing
        manager.repo.get_by_id.return_value = existing

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            confirmed=True,
        )

        assert result.new_confidence <= 1.0

    def test_no_status_change_when_not_enough_confirmations(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        # High confidence but only 1 confirmation — not enough
        existing = _make_pattern(
            confidence=0.65,
            times_confirmed=0,
            status="hypothesis",
        )
        manager.repo.find_matching.return_value = existing
        manager.repo.get_by_id.return_value = existing

        result = manager.detect_or_update_pattern(
            user_id=1,
            pattern_type="correlation",
            input_signals=["late_caffeine"],
            output_signal="hrv_rmssd",
            confirmed=True,
        )

        # High confidence but not enough confirmations
        # times_confirmed was 0, now 1 (from this observation), need >= 3
        assert result.status_changed is False


class TestInvalidatePattern:
    """Test explicit pattern invalidation."""

    def test_invalidate_existing(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        pattern = _make_pattern(status="confirmed")
        manager.repo.get_by_id.return_value = pattern
        manager.repo.update_status.return_value = pattern

        result = manager.invalidate_pattern(1, "contradicted by new data")

        manager.repo.update_status.assert_called_with(1, "deprecated")

    def test_invalidate_nonexistent(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()
        manager.repo.get_by_id.return_value = None

        result = manager.invalidate_pattern(999)
        assert result is None


class TestGetPatterns:
    """Test pattern retrieval."""

    def test_get_active_patterns(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        patterns = [
            _make_pattern(status="hypothesis", confidence=0.4),
            _make_pattern(status="confirmed", confidence=0.8),
        ]
        manager.repo.list_active.return_value = patterns

        result = manager.get_active_patterns(user_id=1)
        assert len(result) == 2

    def test_get_confirmed_patterns(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        patterns = [_make_pattern(status="confirmed", confidence=0.8)]
        manager.repo.list_confirmed.return_value = patterns

        result = manager.get_confirmed_patterns(user_id=1)
        assert len(result) == 1

    def test_get_patterns_for_signal(self):
        db = MagicMock()
        manager = PatternManager(db)
        manager.repo = MagicMock()

        patterns = [_make_pattern(output_signal="hrv_rmssd")]
        manager.repo.list_active.return_value = patterns

        result = manager.get_patterns_for_signal(user_id=1, signal="hrv_rmssd")
        assert len(result) == 1
        manager.repo.list_active.assert_called_with(user_id=1, output_signal="hrv_rmssd")


class TestConfidenceUpdateMath:
    """Test the confidence update math directly."""

    def test_confirm_increases_confidence(self):
        """Confirming should always increase confidence."""
        for initial in [0.1, 0.3, 0.5, 0.7, 0.9]:
            new = initial + (1 - initial) * CONFIRM_RATE
            assert new > initial

    def test_contradict_decreases_confidence(self):
        """Contradicting should always decrease confidence."""
        for initial in [0.1, 0.3, 0.5, 0.7, 0.9]:
            new = initial - initial * CONTRADICT_RATE
            assert new < initial

    def test_confirm_approaches_one(self):
        """Repeated confirmations should approach but never exceed 1.0."""
        confidence = 0.3
        for _ in range(50):
            confidence = confidence + (1 - confidence) * CONFIRM_RATE
        assert confidence < 1.0
        assert confidence > 0.95

    def test_contradict_approaches_zero(self):
        """Repeated contradictions should approach but never reach 0."""
        confidence = 0.9
        for _ in range(50):
            confidence = confidence - confidence * CONTRADICT_RATE
        assert confidence > 0.0
        assert confidence < 0.01
