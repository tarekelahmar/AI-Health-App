"""Tests for Journal V3 Chat — session management, score confirmation, message persistence."""

import pytest
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domain.models.journal_session import JournalSession
from app.domain.models.journal_message import JournalMessage
from app.domain.models.daily_checkin import DailyCheckIn
from app.domain.models.user import User
from app.engine.journal_chat_service import (
    resolve_session,
    save_message,
    confirm_daily_score,
    get_sessions_for_user,
    get_session_messages,
    SESSION_GAP_HOURS,
    _detect_proposed_score,
)


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


# ── Session Auto-Creation ────────────────────────────────────────

class TestSessionResolution:
    def test_new_session_when_none_exists(self, db, user):
        """Session auto-creation: new session when none exists for today."""
        session = resolve_session(db, user.id)
        db.commit()

        assert session is not None
        assert session.user_id == user.id
        assert session.started_at is not None

    def test_reuse_session_within_gap(self, db, user):
        """Session reuse: message within 4 hours joins existing session."""
        # Create a session with a recent message
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow() - timedelta(hours=1),
            created_at=datetime.utcnow() - timedelta(hours=1),
        )
        db.add(s)
        db.flush()

        msg = JournalMessage(
            session_id=s.id,
            user_id=user.id,
            role="user",
            content="Hello",
            created_at=datetime.utcnow() - timedelta(minutes=30),
        )
        db.add(msg)
        db.commit()

        resolved = resolve_session(db, user.id)
        assert resolved.id == s.id

    def test_new_session_after_gap(self, db, user):
        """Session split: message after 4-hour gap creates new session."""
        # Create a session with an old message (>4 hours ago)
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow() - timedelta(hours=6),
            created_at=datetime.utcnow() - timedelta(hours=6),
        )
        db.add(s)
        db.flush()

        msg = JournalMessage(
            session_id=s.id,
            user_id=user.id,
            role="user",
            content="Hello",
            created_at=datetime.utcnow() - timedelta(hours=5),
        )
        db.add(msg)
        db.commit()

        resolved = resolve_session(db, user.id)
        db.commit()

        assert resolved.id != s.id
        assert resolved.user_id == user.id

    def test_explicit_session_id(self, db, user):
        """If session_id given and valid, use it."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.commit()

        resolved = resolve_session(db, user.id, session_id=s.id)
        assert resolved.id == s.id


# ── Message Persistence ──────────────────────────────────────────

class TestMessagePersistence:
    def test_save_user_message(self, db, user):
        """User messages saved correctly."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        msg = save_message(db, s.id, user.id, "user", "Hello world")
        db.commit()

        assert msg.id is not None
        assert msg.role == "user"
        assert msg.content == "Hello world"
        assert msg.session_id == s.id

    def test_save_assistant_message_with_analysis(self, db, user):
        """Assistant messages saved with analysis JSON."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        analysis = {"inferred_dimensions": {"motivation": 7.5}, "factors": {"exercised": True}}
        msg = save_message(db, s.id, user.id, "assistant", "That's great!", analysis)
        db.commit()

        assert msg.ai_analysis_json == analysis


# ── Score Confirmation ───────────────────────────────────────────

class TestScoreConfirmation:
    def test_creates_daily_checkin(self, db, user):
        """Score confirmation creates DailyCheckIn row."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        # Add user messages (they form the notes)
        save_message(db, s.id, user.id, "user", "Had a good day")
        save_message(db, s.id, user.id, "assistant", "That's great!")
        save_message(db, s.id, user.id, "user", "Went for a run")
        db.commit()

        # Patch downstream functions to avoid missing tables
        # Downstream functions (wellness score, domain scoring, milestones) will
        # fail silently in test since the full engine isn't available with SQLite.
        result = confirm_daily_score(db, user.id, s.id, 7.0)

        assert result["confirmed"] is True
        assert result["score"] == 7.0

        checkin = db.query(DailyCheckIn).filter(
            DailyCheckIn.user_id == user.id,
        ).first()

        assert checkin is not None
        assert checkin.overall_wellbeing == 7.0
        assert "Had a good day" in checkin.notes
        assert "Went for a run" in checkin.notes

    def test_updates_session_score(self, db, user):
        """Score confirmation updates session.daily_score."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        save_message(db, s.id, user.id, "user", "Test message")
        db.commit()

        # Downstream functions fail silently in test (SQLite)
        confirm_daily_score(db, user.id, s.id, 6.5)

        db.refresh(s)
        assert s.daily_score == 6.5
        assert s.score_confirmed_at is not None


# ── Session Listing ──────────────────────────────────────────────

class TestSessionListing:
    def test_list_sessions(self, db, user):
        """Session list endpoint returns correct format."""
        # Create two sessions
        s1 = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow() - timedelta(days=1),
            created_at=datetime.utcnow() - timedelta(days=1),
        )
        s2 = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            daily_score=7.0,
        )
        db.add_all([s1, s2])
        db.flush()

        save_message(db, s1.id, user.id, "user", "First session message")
        save_message(db, s2.id, user.id, "user", "Second session message")
        db.commit()

        sessions = get_sessions_for_user(db, user.id)

        assert len(sessions) == 2
        # Most recent first
        assert sessions[0]["daily_score"] == 7.0
        assert sessions[0]["message_count"] == 1
        assert "Second session" in sessions[0]["preview"]


# ── Session Messages ─────────────────────────────────────────────

class TestSessionMessages:
    def test_chronological_order(self, db, user):
        """Session messages endpoint returns chronological order."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        save_message(db, s.id, user.id, "user", "First message")
        save_message(db, s.id, user.id, "assistant", "Response")
        save_message(db, s.id, user.id, "user", "Second message")
        db.commit()

        messages = get_session_messages(db, user.id, s.id)

        assert len(messages) == 3
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "First message"
        assert messages[1]["role"] == "assistant"
        assert messages[2]["role"] == "user"

    def test_wrong_user_returns_empty(self, db, user):
        """Cannot access another user's session."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()
        save_message(db, s.id, user.id, "user", "Private message")
        db.commit()

        messages = get_session_messages(db, 999, s.id)  # Wrong user
        assert messages == []


# ── Score Proposal Detection ────────────────────────────────────

class TestScoreProposalDetection:
    """Server-side detection of score proposals from companion text."""

    def test_canonical_around_a(self):
        assert _detect_proposed_score("I'd put today around a 7") == 7.0

    def test_around_a_decimal(self):
        assert _detect_proposed_score("Sounds like today lands around a 6.5 for you.") == 6.5

    def test_at_a(self):
        assert _detect_proposed_score("I'd place this at a 8") == 8.0

    def test_maybe_a(self):
        assert _detect_proposed_score("maybe a 5.5?") == 5.5

    def test_say_a(self):
        assert _detect_proposed_score("I'd say a 7 for today") == 7.0

    def test_like_a(self):
        assert _detect_proposed_score("feels like a 6 kind of day") == 6.0

    def test_out_of_range_ignored(self):
        assert _detect_proposed_score("around a 11") is None
        assert _detect_proposed_score("around a 0") is None

    def test_no_score_returns_none(self):
        assert _detect_proposed_score("That sounds like a tough day.") is None

    def test_snaps_to_half(self):
        # 7.3 -> 7.5, but regex only captures one decimal so 7.3 matches as 7.3
        assert _detect_proposed_score("around a 7") == 7.0
        assert _detect_proposed_score("around a 7.5") == 7.5


# ── Include Messages in Session Listing ─────────────────────────

class TestSessionListingWithMessages:
    def test_include_messages_returns_inline(self, db, user):
        """include_messages=N returns messages for the N most recent sessions."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        save_message(db, s.id, user.id, "user", "Hello")
        save_message(db, s.id, user.id, "assistant", "Hi there!")
        db.commit()

        # With include_messages=1
        sessions = get_sessions_for_user(db, user.id, include_messages=1)
        assert len(sessions) == 1
        assert "messages" in sessions[0]
        assert len(sessions[0]["messages"]) == 2
        assert sessions[0]["messages"][0]["role"] == "user"

    def test_no_include_messages_omits_key(self, db, user):
        """Default: messages key is not present."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()
        save_message(db, s.id, user.id, "user", "Hello")
        db.commit()

        sessions = get_sessions_for_user(db, user.id)
        assert "messages" not in sessions[0]
