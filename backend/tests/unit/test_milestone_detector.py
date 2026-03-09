"""Tests for milestone_detector.py — all 5 milestone types."""

import pytest
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.engine.milestone_detector import (
    _is_real_entry,
    check_score_streak,
    check_recovery,
    check_consistency,
    DetectedMilestone,
)


def _make_entry(wb=None, word_count=None, checkin_date=None):
    e = MagicMock()
    e.overall_wellbeing = wb
    e.word_count = word_count
    e.checkin_date = checkin_date or date.today()
    return e


# ── _is_real_entry ────────────────────────────────────────────────

class TestIsRealEntry:
    def test_real_with_wellbeing(self):
        assert _is_real_entry(_make_entry(wb=7.0)) is True

    def test_real_with_word_count(self):
        assert _is_real_entry(_make_entry(word_count=50)) is True

    def test_placeholder(self):
        assert _is_real_entry(_make_entry()) is False

    def test_zero_word_count_is_placeholder(self):
        assert _is_real_entry(_make_entry(word_count=0)) is False


# ── check_score_streak ────────────────────────────────────────────

class TestScoreStreak:
    def test_streak_of_5(self):
        entries = [_make_entry(wb=8.0) for _ in range(5)] + [_make_entry(wb=3.0) for _ in range(5)]
        result = check_score_streak(entries)
        assert result is not None
        assert result.milestone_type == "score_streak"
        assert result.metadata["streak_days"] >= 5

    def test_no_streak(self):
        entries = [_make_entry(wb=3.0)] + [_make_entry(wb=8.0)] * 5
        result = check_score_streak(entries)
        assert result is None

    def test_insufficient_data(self):
        entries = [_make_entry(wb=8.0) for _ in range(3)]
        result = check_score_streak(entries)
        assert result is None

    def test_all_equal(self):
        entries = [_make_entry(wb=5.0) for _ in range(10)]
        result = check_score_streak(entries)
        # avg=5.0, all scores >= avg → streak of 10
        assert result is not None
        assert result.metadata["streak_days"] == 10


# ── check_recovery ────────────────────────────────────────────────

class TestRecovery:
    def test_recovery_detected(self):
        entries = [
            _make_entry(wb=8.0),  # today
            _make_entry(wb=4.0),  # yesterday (trough)
            _make_entry(wb=5.0),
            _make_entry(wb=6.0),
        ]
        result = check_recovery(entries)
        assert result is not None
        assert result.milestone_type == "recovery"
        assert result.metadata["climb"] == 4.0

    def test_no_recovery_small_climb(self):
        entries = [
            _make_entry(wb=6.0),
            _make_entry(wb=5.0),
            _make_entry(wb=5.5),
        ]
        result = check_recovery(entries)
        assert result is None

    def test_insufficient_data(self):
        entries = [_make_entry(wb=8.0)]
        result = check_recovery(entries)
        assert result is None


# ── check_consistency ─────────────────────────────────────────────

class TestConsistency:
    def test_14_day_streak(self):
        today = date.today()
        entries = [
            _make_entry(wb=6.0, checkin_date=today - timedelta(days=i))
            for i in range(14)
        ]
        result = check_consistency(entries)
        assert result is not None
        assert result.milestone_type == "consistency"
        assert result.metadata["streak_days"] == 14

    def test_gap_breaks_streak(self):
        today = date.today()
        entries = []
        for i in range(7):
            entries.append(_make_entry(wb=6.0, checkin_date=today - timedelta(days=i)))
        # Skip day 7
        for i in range(8, 16):
            entries.append(_make_entry(wb=6.0, checkin_date=today - timedelta(days=i)))
        result = check_consistency(entries)
        assert result is None

    def test_insufficient_entries(self):
        today = date.today()
        entries = [
            _make_entry(wb=6.0, checkin_date=today - timedelta(days=i))
            for i in range(5)
        ]
        result = check_consistency(entries)
        assert result is None

    def test_20_day_streak(self):
        today = date.today()
        entries = [
            _make_entry(wb=6.0, checkin_date=today - timedelta(days=i))
            for i in range(20)
        ]
        result = check_consistency(entries)
        assert result is not None
        assert result.metadata["streak_days"] == 20
