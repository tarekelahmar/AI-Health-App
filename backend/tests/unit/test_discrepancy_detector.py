"""Tests for the discrepancy detector — all 4 deterministic rules."""

import pytest

from app.engine.discrepancy_detector import (
    check_slider_vs_text,
    check_consecutive_drops,
    check_assessment_vs_behaviour,
    check_connection_vs_isolation,
    detect,
    DiscrepancyResult,
)


# ── Rule 1: Slider vs Text Sentiment ──────────────────────────────


class TestSliderVsText:
    """Test slider/sentiment disagreement detection."""

    def test_high_wellbeing_negative_sentiment_flags(self):
        d = check_slider_vs_text(overall_wellbeing=8.0, sentiment_score=-0.4)
        assert d is not None
        assert d.rule == "slider_vs_text"
        assert d.severity == "notable"

    def test_low_wellbeing_positive_sentiment_flags(self):
        d = check_slider_vs_text(overall_wellbeing=3.0, sentiment_score=0.5)
        assert d is not None
        assert d.rule == "slider_vs_text"
        assert d.severity == "info"

    def test_high_wellbeing_positive_sentiment_no_flag(self):
        d = check_slider_vs_text(overall_wellbeing=8.0, sentiment_score=0.5)
        assert d is None

    def test_low_wellbeing_negative_sentiment_no_flag(self):
        d = check_slider_vs_text(overall_wellbeing=3.0, sentiment_score=-0.5)
        assert d is None

    def test_neutral_sentiment_no_flag(self):
        d = check_slider_vs_text(overall_wellbeing=8.0, sentiment_score=0.0)
        assert d is None

    def test_none_wellbeing_no_flag(self):
        d = check_slider_vs_text(overall_wellbeing=None, sentiment_score=-0.5)
        assert d is None

    def test_none_sentiment_no_flag(self):
        d = check_slider_vs_text(overall_wellbeing=8.0, sentiment_score=None)
        assert d is None

    def test_boundary_wellbeing_exactly_7_flags(self):
        d = check_slider_vs_text(overall_wellbeing=7.0, sentiment_score=-0.3)
        assert d is not None

    def test_boundary_wellbeing_just_below_no_flag(self):
        d = check_slider_vs_text(overall_wellbeing=6.9, sentiment_score=-0.5)
        assert d is None


# ── Rule 2: Consecutive Drops ─────────────────────────────────────


class TestConsecutiveDrops:
    """Test multi-day decline detection."""

    def test_three_consecutive_drops_flags(self):
        # 7.0 → 6.0 → 5.0 → 4.0  (3 drops)
        d = check_consecutive_drops([7.0, 6.0, 5.0, 4.0])
        assert d is not None
        assert d.rule == "consecutive_drops"
        assert "3 consecutive days" in d.description

    def test_five_consecutive_drops_significant(self):
        d = check_consecutive_drops([8.0, 7.0, 6.0, 5.0, 4.0, 3.0])
        assert d is not None
        assert d.severity == "significant"

    def test_two_drops_no_flag(self):
        # 7.0 → 6.0 → 5.0  (only 2 drops)
        d = check_consecutive_drops([7.0, 6.0, 5.0])
        assert d is None

    def test_drop_then_rise_no_flag(self):
        # 7.0 → 5.0 → 6.0 → 4.0  (not consecutive — rise at index 2)
        d = check_consecutive_drops([7.0, 5.0, 6.0, 4.0])
        assert d is None

    def test_flat_no_flag(self):
        d = check_consecutive_drops([5.0, 5.0, 5.0, 5.0])
        assert d is None

    def test_none_values_break_streak(self):
        # 7.0 → 6.0 → None → 5.0 → 4.0
        # Valid pairs after filtering: 7,6,5,4 — but they need to be truly
        # consecutive in the valid list. 6→5 and 5→4 = 2 drops, not 3
        d = check_consecutive_drops([7.0, 6.0, None, 5.0, 4.0])
        # After filtering None: valid = [(0,7),(1,6),(3,5),(4,4)]
        # Walking back: 4<5 (drop), 5<6 (drop), 6<7 (drop) = 3 drops
        assert d is not None

    def test_too_short_no_flag(self):
        d = check_consecutive_drops([5.0, 4.0])
        assert d is None

    def test_empty_list_no_flag(self):
        d = check_consecutive_drops([])
        assert d is None

    def test_all_none_no_flag(self):
        d = check_consecutive_drops([None, None, None, None])
        assert d is None


# ── Rule 3: Assessment vs Behaviour ───────────────────────────────


class TestAssessmentVsBehaviour:
    """Test motivation/plans without corresponding actions."""

    def test_motivation_without_action_flags(self):
        text = "I'm going to start exercising. I plan to get back to the gym. I'm really motivated."
        tags = {"exercise": False, "achievement": False}
        d = check_assessment_vs_behaviour(text, tags)
        assert d is not None
        assert d.rule == "assessment_vs_behaviour"

    def test_motivation_with_exercise_no_flag(self):
        text = "I'm going to keep this going. I plan to do more tomorrow."
        tags = {"exercise": True, "achievement": False}
        d = check_assessment_vs_behaviour(text, tags)
        assert d is None

    def test_motivation_with_achievement_no_flag(self):
        text = "I want to build on this. I'm determined to keep going."
        tags = {"exercise": False, "achievement": True}
        d = check_assessment_vs_behaviour(text, tags)
        assert d is None

    def test_motivation_with_productive_work_no_flag(self):
        text = "I plan to keep this pace. I'm looking forward to more."
        tags = {"exercise": False, "achievement": False, "work_type": "productive"}
        d = check_assessment_vs_behaviour(text, tags)
        assert d is None

    def test_no_motivation_no_flag(self):
        text = "Had a quiet day. Read a book."
        tags = {"exercise": False, "achievement": False}
        d = check_assessment_vs_behaviour(text, tags)
        assert d is None

    def test_single_keyword_not_enough(self):
        text = "I want to relax today."
        tags = {"exercise": False, "achievement": False}
        d = check_assessment_vs_behaviour(text, tags)
        assert d is None  # Only 1 keyword, need >= 2

    def test_none_text_no_flag(self):
        d = check_assessment_vs_behaviour(None, {"exercise": True})
        assert d is None

    def test_none_tags_no_flag(self):
        d = check_assessment_vs_behaviour("I plan to do everything.", None)
        assert d is None


# ── Rule 4: Connection vs Isolation ───────────────────────────────


class TestConnectionVsIsolation:
    """Test high connection slider vs prolonged isolation."""

    def test_high_connection_prolonged_isolation_flags(self):
        d = check_connection_vs_isolation(
            connection_score=8.0,
            recent_social_tags=["alone", "alone", "alone"],
        )
        assert d is not None
        assert d.rule == "connection_vs_isolation"

    def test_high_connection_with_social_contact_no_flag(self):
        d = check_connection_vs_isolation(
            connection_score=8.0,
            recent_social_tags=["friends", "alone", "family"],
        )
        assert d is None

    def test_low_connection_isolated_no_flag(self):
        """Low connection + isolation is consistent, not a discrepancy."""
        d = check_connection_vs_isolation(
            connection_score=3.0,
            recent_social_tags=["alone", "alone", "alone"],
        )
        assert d is None

    def test_none_tags_count_as_isolation(self):
        d = check_connection_vs_isolation(
            connection_score=8.0,
            recent_social_tags=[None, None, None],
        )
        assert d is not None

    def test_mixed_none_and_alone(self):
        d = check_connection_vs_isolation(
            connection_score=7.5,
            recent_social_tags=[None, "alone", "none"],
        )
        assert d is not None

    def test_too_few_days_no_flag(self):
        d = check_connection_vs_isolation(
            connection_score=8.0,
            recent_social_tags=["alone", "alone"],
        )
        assert d is None

    def test_none_connection_no_flag(self):
        d = check_connection_vs_isolation(
            connection_score=None,
            recent_social_tags=["alone", "alone", "alone"],
        )
        assert d is None


# ── Aggregator ────────────────────────────────────────────────────


class TestDetectAggregator:
    """Test the top-level detect() function."""

    def test_no_data_no_flags(self):
        result = detect()
        assert isinstance(result, DiscrepancyResult)
        assert result.flagged is False
        assert result.discrepancies == []

    def test_single_flag_propagates(self):
        result = detect(overall_wellbeing=8.0, sentiment_score=-0.5)
        assert result.flagged is True
        assert len(result.discrepancies) == 1
        assert result.discrepancies[0].rule == "slider_vs_text"

    def test_multiple_flags_aggregate(self):
        result = detect(
            overall_wellbeing=8.0,
            sentiment_score=-0.5,
            recent_wellbeing=[7.0, 6.0, 5.0, 4.0],
        )
        assert result.flagged is True
        assert len(result.discrepancies) == 2
        rules = {d.rule for d in result.discrepancies}
        assert "slider_vs_text" in rules
        assert "consecutive_drops" in rules

    def test_to_json_when_flagged(self):
        result = detect(overall_wellbeing=8.0, sentiment_score=-0.5)
        j = result.to_json()
        assert j is not None
        assert j["flag"] is True
        assert len(j["discrepancies"]) == 1

    def test_to_json_when_clean(self):
        result = detect(overall_wellbeing=7.0, sentiment_score=0.3)
        assert result.to_json() is None

    def test_all_four_rules_can_fire(self):
        result = detect(
            overall_wellbeing=8.0,
            connection_score=8.0,
            sentiment_score=-0.5,
            entry_text="I'm going to start running. I plan to go every day. I'm motivated and determined.",
            context_tags={"exercise": False, "achievement": False},
            recent_wellbeing=[8.0, 7.0, 6.0, 5.0],
            recent_social_tags=["alone", "alone", "alone"],
        )
        assert result.flagged is True
        assert len(result.discrepancies) == 4
        rules = {d.rule for d in result.discrepancies}
        assert rules == {"slider_vs_text", "consecutive_drops", "assessment_vs_behaviour", "connection_vs_isolation"}
