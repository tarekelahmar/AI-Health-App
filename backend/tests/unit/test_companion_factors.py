"""Tests for companion today's-factor context and system prompt enhancements."""

import pytest
from datetime import datetime, date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domain.models.user import User
from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.journal_session import JournalSession
from app.domain.models.journal_message import JournalMessage
from app.engine.journal_companion import _format_today_factors
from app.engine.prompts.journal_chat_system import build_chat_system_prompt


# ── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture
def db():
    """In-memory SQLite session for testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def user(db):
    """Create a test user."""
    u = User(
        id=1,
        email="test@example.com",
        hashed_password="fake",
        created_at=datetime.utcnow(),
    )
    db.add(u)
    db.commit()
    return u


# ── _format_today_factors Tests ──────────────────────────────────

class TestFormatTodayFactors:
    def test_no_checkin_returns_default_message(self, db, user):
        """When no DailyCheckIn exists, returns default message."""
        result = _format_today_factors(db, user.id)
        assert result == "No behavioral factors tracked today yet."

    def test_checkin_with_behaviors(self, db, user):
        """When DailyCheckIn has behaviors_json, formats done/not done."""
        today = date.today()
        checkin = DailyCheckIn(
            user_id=user.id,
            checkin_date=today,
            overall_wellbeing=7.0,
            behaviors_json={
                "exercised": True,
                "social_contact": True,
                "alcohol": False,
                "meditation": False,
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(checkin)
        db.commit()

        result = _format_today_factors(db, user.id)

        assert "TODAY'S BEHAVIORAL FACTORS:" in result
        assert "Done:" in result
        assert "Exercised" in result
        assert "Social Contact" in result
        assert "Not done:" in result
        assert "Alcohol" in result
        assert "Meditation" in result

    def test_checkin_with_empty_behaviors(self, db, user):
        """When behaviors_json is empty dict, falls through to tier 2."""
        today = date.today()
        checkin = DailyCheckIn(
            user_id=user.id,
            checkin_date=today,
            overall_wellbeing=7.0,
            behaviors_json={},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(checkin)
        db.commit()

        result = _format_today_factors(db, user.id)
        # Empty behaviors_json is falsy, so falls to tier 2, then to default
        assert "No behavioral factors tracked today yet." in result

    def test_checkin_with_null_behaviors(self, db, user):
        """When behaviors_json is None, falls through to tier 2."""
        today = date.today()
        checkin = DailyCheckIn(
            user_id=user.id,
            checkin_date=today,
            overall_wellbeing=7.0,
            behaviors_json=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(checkin)
        db.commit()

        result = _format_today_factors(db, user.id)
        assert "No behavioral factors tracked today yet." in result

    def test_tier2_session_analysis_fallback(self, db, user):
        """When no DailyCheckIn but session has analysis, uses session factors."""
        now = datetime.utcnow()
        session = JournalSession(
            id=1,
            user_id=user.id,
            started_at=now,
            created_at=now,
        )
        db.add(session)
        db.flush()

        # Assistant message with analysis containing factors
        msg = JournalMessage(
            session_id=session.id,
            user_id=user.id,
            role="assistant",
            content="I hear you",
            ai_analysis_json={
                "factors": {
                    "exercised": True,
                    "structured_day": False,
                    "outdoors": True,
                },
            },
            created_at=now,
        )
        db.add(msg)
        db.commit()

        result = _format_today_factors(db, user.id)

        assert "TODAY'S BEHAVIORAL FACTORS:" in result
        assert "Exercised" in result
        assert "Outdoors" in result
        assert "Structured Day" in result

    def test_tier2_only_checks_today_sessions(self, db, user):
        """Session from yesterday should NOT be used as fallback."""
        yesterday = datetime.utcnow() - timedelta(days=1)
        session = JournalSession(
            id=1,
            user_id=user.id,
            started_at=yesterday,
            created_at=yesterday,
        )
        db.add(session)
        db.flush()

        msg = JournalMessage(
            session_id=session.id,
            user_id=user.id,
            role="assistant",
            content="Yesterday's response",
            ai_analysis_json={
                "factors": {"exercised": True},
            },
            created_at=yesterday,
        )
        db.add(msg)
        db.commit()

        result = _format_today_factors(db, user.id)
        assert result == "No behavioral factors tracked today yet."

    def test_tier1_takes_precedence_over_tier2(self, db, user):
        """DailyCheckIn behaviors should be used even when session analysis exists."""
        now = datetime.utcnow()
        today = date.today()

        # Tier 1: DailyCheckIn with different factors
        checkin = DailyCheckIn(
            user_id=user.id,
            checkin_date=today,
            overall_wellbeing=7.0,
            behaviors_json={"exercised": True, "meditation": True},
            created_at=now,
            updated_at=now,
        )
        db.add(checkin)

        # Tier 2: Session with different factors
        session = JournalSession(
            id=1,
            user_id=user.id,
            started_at=now,
            created_at=now,
        )
        db.add(session)
        db.flush()

        msg = JournalMessage(
            session_id=session.id,
            user_id=user.id,
            role="assistant",
            content="Response",
            ai_analysis_json={
                "factors": {"alcohol": True, "isolated": True},
            },
            created_at=now,
        )
        db.add(msg)
        db.commit()

        result = _format_today_factors(db, user.id)

        # Should have tier 1 factors (exercised, meditation), not tier 2
        assert "Exercised" in result
        assert "Meditation" in result
        assert "Alcohol" not in result
        assert "Isolated" not in result

    def test_only_boolean_factors_formatted(self, db, user):
        """Non-boolean factors should be silently skipped."""
        today = date.today()
        checkin = DailyCheckIn(
            user_id=user.id,
            checkin_date=today,
            overall_wellbeing=7.0,
            behaviors_json={
                "exercised": True,
                "exercise_type": "running",  # string, not bool
                "exercise_minutes": 30,  # int, not bool
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(checkin)
        db.commit()

        result = _format_today_factors(db, user.id)
        assert "Exercised" in result
        assert "exercise_type" not in result.lower()
        assert "exercise_minutes" not in result.lower()


# ── System Prompt Tests ──────────────────────────────────────────

class TestBuildChatSystemPrompt:
    def test_includes_today_factors_text(self):
        """System prompt includes the today_factors placeholder content."""
        prompt = build_chat_system_prompt(
            today_factors_text="TODAY'S BEHAVIORAL FACTORS:\n  Done: Exercised, Meditation"
        )
        assert "TODAY'S BEHAVIORAL FACTORS:" in prompt
        assert "Exercised" in prompt
        assert "Meditation" in prompt

    def test_includes_pattern_aware_actions_section(self):
        """System prompt includes the PATTERN-AWARE ACTIONS instruction block."""
        prompt = build_chat_system_prompt()
        assert "PATTERN-AWARE ACTIONS:" in prompt
        assert "floor factor" in prompt
        assert "crash pattern" in prompt

    def test_default_today_factors_message(self):
        """Without explicit today_factors_text, uses default message."""
        prompt = build_chat_system_prompt()
        assert "No behavioral factors tracked today yet." in prompt

    def test_all_context_sections_present(self):
        """All context sections are present in the assembled prompt."""
        prompt = build_chat_system_prompt(
            active_patterns_text="ACTIVE PATTERNS: test",
            rolling_summary_text="USER SUMMARY: test",
            previous_session_text="PREV SESSION: test",
            today_factors_text="TODAY FACTORS: test",
        )
        assert "ACTIVE PATTERNS: test" in prompt
        assert "USER SUMMARY: test" in prompt
        assert "PREV SESSION: test" in prompt
        assert "TODAY FACTORS: test" in prompt
        assert "PATTERN-AWARE ACTIONS:" in prompt
        assert "STRICT RULES" in prompt
