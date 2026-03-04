"""Tests for journal_synthesis.py — phase classification and template helpers."""

import pytest

from app.engine.journal_synthesis import (
    classify_phase,
    _generate_weekly_question,
    _build_phase_narrative,
    _identify_focus_areas,
)


# ── Phase Classification ──────────────────────────────────────────

class TestClassifyPhase:
    def test_crisis(self):
        # avg < 3.0 and volatility > 2.0
        result = classify_phase([1.0, 7.0, 1.0, 1.0, 1.0], entry_count=5)
        assert result.phase == "CRISIS"

    def test_stable(self):
        result = classify_phase([6.0, 6.5, 6.0, 7.0, 6.5], entry_count=5)
        assert result.phase == "STABLE"

    def test_growing(self):
        result = classify_phase([5.0, 5.5, 6.0, 7.0, 7.5, 8.0], entry_count=6)
        assert result.phase == "GROWING"

    def test_stabilizing_volatile(self):
        result = classify_phase([3.0, 8.0, 2.0, 9.0, 4.0], entry_count=5)
        assert result.phase == "STABILIZING"

    def test_empty_data(self):
        result = classify_phase([], entry_count=0)
        assert result.phase == "STABLE"
        assert result.confidence == 0.0

    def test_confidence_scales(self):
        result = classify_phase([6.0, 6.5], entry_count=2)
        assert result.confidence == 0.4  # 2/5

    def test_full_confidence(self):
        result = classify_phase([6.0] * 7, entry_count=7)
        assert result.confidence == 1.0


# ── Weekly Question Templates ─────────────────────────────────────

class TestWeeklyQuestion:
    def test_down_trend(self):
        q = _generate_weekly_question("down", 4.0, None)
        assert "shift" in q.lower() or "change" in q.lower()

    def test_up_trend(self):
        q = _generate_weekly_question("up", 7.0, None)
        assert "working" in q.lower() or "keep" in q.lower()

    def test_with_pattern(self):
        q = _generate_weekly_question("stable", 6.0, "Morning Exercise")
        assert "Morning Exercise" in q

    def test_default(self):
        q = _generate_weekly_question("stable", 6.0, None)
        assert "week" in q.lower()


# ── Phase Narrative ───────────────────────────────────────────────

class TestPhaseNarrative:
    def test_single_phase(self):
        phases = [{"phase": "STABLE", "confidence": 1.0}]
        n = _build_phase_narrative(phases, 6.5, 7)
        assert "stable" in n.lower()
        assert "6.5" in n

    def test_transition(self):
        phases = [
            {"phase": "STABILIZING", "confidence": 0.8},
            {"phase": "STABLE", "confidence": 1.0},
        ]
        n = _build_phase_narrative(phases, 5.5, 10)
        assert "STABILIZING -> STABLE" in n

    def test_empty(self):
        n = _build_phase_narrative([], None, 0)
        assert "not enough" in n.lower()


# ── Focus Areas ───────────────────────────────────────────────────

class TestFocusAreas:
    def test_low_domains(self):
        scores = {"Career & Work": 4.0, "Relationship": 7.0, "Finance": 3.5}
        areas = _identify_focus_areas(scores, [])
        assert len(areas) == 2
        assert "Finance" in areas[0]

    def test_all_good(self):
        scores = {"Career & Work": 7.0, "Relationship": 8.0}
        areas = _identify_focus_areas(scores, [])
        assert "tracking well" in areas[0].lower()
