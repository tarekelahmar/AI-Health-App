"""Tests for the life domain scoring service — EMA logic and signal derivation."""

import pytest
from unittest.mock import MagicMock

from app.engine.life_domain_scorer import (
    ema_update,
    _derive_signals_from_sliders,
    _derive_signals_from_context_tags,
    _derive_signals_from_companion,
    EMA_ALPHA,
)


# ── EMA Core ──────────────────────────────────────────────────────


class TestEmaUpdate:
    def test_basic_update(self):
        # alpha=0.3: new = 0.3*8 + 0.7*5 = 2.4 + 3.5 = 5.9
        result = ema_update(5.0, 8.0)
        assert abs(result - 5.9) < 0.01

    def test_stable_when_same(self):
        result = ema_update(5.0, 5.0)
        assert abs(result - 5.0) < 0.01

    def test_clamped_high(self):
        result = ema_update(9.5, 15.0)
        assert result == 10.0

    def test_clamped_low(self):
        result = ema_update(1.5, -5.0)
        assert result == 1.0

    def test_custom_alpha(self):
        # alpha=0.5: new = 0.5*8 + 0.5*4 = 6.0
        result = ema_update(4.0, 8.0, alpha=0.5)
        assert abs(result - 6.0) < 0.01

    def test_convergence_over_time(self):
        """EMA converges to the signal value with repeated updates."""
        score = 5.0
        for _ in range(30):
            score = ema_update(score, 9.0)
        assert abs(score - 9.0) < 0.1


# ── Slider Signal Derivation ─────────────────────────────────────


class TestSliderSignals:
    def _make_checkin(self, **kwargs):
        mock = MagicMock()
        for attr in ["overall_wellbeing", "energy", "mood", "focus", "connection"]:
            setattr(mock, attr, kwargs.get(attr, None))
        return mock

    def test_full_sliders(self):
        checkin = self._make_checkin(
            overall_wellbeing=8.0, energy=7.0, mood=6.0, focus=5.0, connection=9.0,
        )
        signals = _derive_signals_from_sliders(checkin)
        assert "mental_emotional" in signals
        assert "physical_health" in signals
        assert "career_work" in signals
        assert "social_friendships" in signals

    def test_no_sliders(self):
        checkin = self._make_checkin()
        signals = _derive_signals_from_sliders(checkin)
        assert signals == {}

    def test_energy_maps_to_physical_health(self):
        checkin = self._make_checkin(energy=9.0)
        signals = _derive_signals_from_sliders(checkin)
        assert "physical_health" in signals
        # energy maps: physical_health=0.8, structure_routine=0.2
        # weighted avg: (9*0.8 + 9*0.2) / (0.8+0.2) = 9.0 (only one slider)
        assert abs(signals["physical_health"] - 9.0) < 0.01

    def test_connection_maps_to_social(self):
        checkin = self._make_checkin(connection=3.0)
        signals = _derive_signals_from_sliders(checkin)
        assert "social_friendships" in signals
        assert signals["social_friendships"] < 5.0


# ── Context Tag Signal Derivation ─────────────────────────────────


class TestContextTagSignals:
    def test_exercise_true(self):
        signals = _derive_signals_from_context_tags({"exercise": True})
        assert "physical_health" in signals
        assert signals["physical_health"] == 7.0

    def test_exercise_false(self):
        signals = _derive_signals_from_context_tags({"exercise": False})
        assert signals == {}

    def test_social_friends(self):
        signals = _derive_signals_from_context_tags({"social_contact": "friends"})
        assert "social_friendships" in signals
        assert signals["social_friendships"] == 7.5

    def test_social_alone(self):
        signals = _derive_signals_from_context_tags({"social_contact": "alone"})
        assert "social_friendships" in signals
        assert signals["social_friendships"] < 5.0

    def test_productive_work(self):
        signals = _derive_signals_from_context_tags({"work_type": "productive"})
        assert "career_work" in signals
        assert "structure_routine" in signals

    def test_conflict(self):
        signals = _derive_signals_from_context_tags({"conflict": True})
        assert "relationship" in signals
        assert signals["relationship"] < 5.0

    def test_achievement(self):
        signals = _derive_signals_from_context_tags({"achievement": True})
        assert "career_work" in signals
        assert "purpose_meaning" in signals

    def test_empty_tags(self):
        assert _derive_signals_from_context_tags({}) == {}

    def test_none_tags(self):
        assert _derive_signals_from_context_tags(None) == {}


# ── Companion Inferred Signal Derivation ──────────────────────────


class TestCompanionSignals:
    def test_motivation(self):
        signals = _derive_signals_from_companion({"motivation": 8.0})
        assert "purpose_meaning" in signals
        assert "career_work" in signals

    def test_self_worth(self):
        signals = _derive_signals_from_companion({"self_worth": 3.0})
        assert "mental_emotional" in signals
        assert signals["mental_emotional"] < 5.0

    def test_structure_adherence(self):
        signals = _derive_signals_from_companion({"structure_adherence": 9.0})
        assert "structure_routine" in signals

    def test_none_dimensions(self):
        assert _derive_signals_from_companion(None) == {}

    def test_null_values_skipped(self):
        signals = _derive_signals_from_companion({
            "motivation": None,
            "self_worth": 7.0,
        })
        # motivation was None → its exclusive domains shouldn't appear
        # But self_worth maps to both mental_emotional (0.7) and purpose_meaning (0.3)
        # So purpose_meaning IS expected from self_worth alone
        assert "mental_emotional" in signals  # self_worth → mental_emotional
        assert "purpose_meaning" in signals   # self_worth → purpose_meaning
        # Verify career_work is NOT present (only motivation maps there)
        assert "career_work" not in signals
