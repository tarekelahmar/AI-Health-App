"""Tests for Domain Check-in — mapping, service, and EMA updates."""

import pytest
from datetime import datetime, date, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base
from app.domain.models.user import User
from app.domain.models.domain_checkin import DomainCheckin
from app.domain.models.life_domain_score import LifeDomainScore, LIFE_DOMAINS, DEFAULT_SCORE
from app.domain.models.journal_session import JournalSession
from app.engine.domain_mapping import (
    expand_to_backend_scores,
    USER_FACING_DOMAINS,
    DOMAIN_KEYS,
)
from app.engine.domain_checkin_service import (
    get_domain_checkin_status,
    save_domain_checkin,
    get_domain_checkin_history,
    CHECKIN_INTERVAL_DAYS,
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


# ── Domain Mapping Tests ─────────────────────────────────────────

class TestDomainMapping:
    def test_expand_to_backend_scores_1_to_1(self):
        """Each user-facing domain maps to exactly one backend column."""
        user_scores = {
            "career": 7.5,
            "relationship": 6.0,
            "social": 8.0,
            "health": 5.5,
            "finance": 4.0,
        }
        result = expand_to_backend_scores(user_scores)

        assert result == {
            "career_work": 7.5,
            "relationship": 6.0,
            "social_friendships": 8.0,
            "physical_health": 5.5,
            "finance": 4.0,
        }

    def test_expand_preserves_exact_values(self):
        """Scores are passed through without transformation."""
        user_scores = {"career": 1.0, "finance": 10.0}
        result = expand_to_backend_scores(user_scores)
        assert result["career_work"] == 1.0
        assert result["finance"] == 10.0

    def test_expand_unknown_key_raises(self):
        """Unknown domain keys raise ValueError."""
        with pytest.raises(ValueError, match="Unknown domain key"):
            expand_to_backend_scores({"bogus": 5.0})

    def test_user_facing_domains_have_required_fields(self):
        """Each domain definition has all required fields."""
        for d in USER_FACING_DOMAINS:
            assert "key" in d
            assert "label" in d
            assert "emoji" in d
            assert "backend_column" in d
            assert "low" in d
            assert "high" in d

    def test_domain_keys_match(self):
        """DOMAIN_KEYS matches USER_FACING_DOMAINS keys."""
        assert DOMAIN_KEYS == [d["key"] for d in USER_FACING_DOMAINS]


# ── Domain Check-in Status Tests ─────────────────────────────────

class TestDomainCheckinStatus:
    def test_due_when_no_checkins(self, db, user):
        """Returns due=True when user has never done a domain check-in."""
        status = get_domain_checkin_status(db, user.id)
        assert status["due"] is True
        assert status["last_checkin_date"] is None
        assert status["days_since"] is None

    def test_not_due_within_7_days(self, db, user):
        """Returns due=False when last check-in is within 7 days."""
        checkin = DomainCheckin(
            user_id=user.id,
            checkin_date=date.today().isoformat(),
            career=5.0, relationship=5.0, social=5.0, health=5.0, finance=5.0,
            created_at=datetime.utcnow(),
        )
        db.add(checkin)
        db.commit()

        status = get_domain_checkin_status(db, user.id)
        assert status["due"] is False
        assert status["days_since"] == 0

    def test_due_after_7_days(self, db, user):
        """Returns due=True when last check-in is >= 7 days ago."""
        old_date = (date.today() - timedelta(days=8)).isoformat()
        checkin = DomainCheckin(
            user_id=user.id,
            checkin_date=old_date,
            career=5.0, relationship=5.0, social=5.0, health=5.0, finance=5.0,
            created_at=datetime.utcnow(),
        )
        db.add(checkin)
        db.commit()

        status = get_domain_checkin_status(db, user.id)
        assert status["due"] is True
        assert status["days_since"] == 8


# ── Domain Check-in Save Tests ───────────────────────────────────

class TestSaveDomainCheckin:
    def test_creates_checkin_row(self, db, user):
        """save_domain_checkin creates a DomainCheckin row."""
        scores = {
            "career": 7.0, "relationship": 6.0,
            "social": 8.0, "health": 5.0, "finance": 4.0,
        }
        checkin = save_domain_checkin(db, user.id, None, scores)
        db.commit()

        assert checkin.id is not None
        assert checkin.career == 7.0
        assert checkin.relationship == 6.0
        assert checkin.social == 8.0
        assert checkin.health == 5.0
        assert checkin.finance == 4.0
        assert checkin.checkin_date == date.today().isoformat()

    def test_upserts_on_same_day(self, db, user):
        """Second save on same day updates existing row (idempotent)."""
        scores1 = {
            "career": 5.0, "relationship": 5.0,
            "social": 5.0, "health": 5.0, "finance": 5.0,
        }
        checkin1 = save_domain_checkin(db, user.id, None, scores1)
        db.commit()
        id1 = checkin1.id

        scores2 = {
            "career": 8.0, "relationship": 7.0,
            "social": 6.0, "health": 9.0, "finance": 3.0,
        }
        checkin2 = save_domain_checkin(db, user.id, None, scores2)
        db.commit()

        assert checkin2.id == id1  # Same row
        assert checkin2.career == 8.0
        assert checkin2.health == 9.0

    def test_updates_life_domain_scores(self, db, user):
        """save_domain_checkin applies EMA to LifeDomainScore."""
        scores = {
            "career": 9.0, "relationship": 8.0,
            "social": 7.0, "health": 6.0, "finance": 5.0,
        }
        save_domain_checkin(db, user.id, None, scores)
        db.commit()

        # Check LifeDomainScore was created/updated
        lds = db.query(LifeDomainScore).filter(
            LifeDomainScore.user_id == user.id,
        ).first()

        assert lds is not None
        # With alpha=0.5 from default 5.0:
        # career_work = 0.5 * 9.0 + 0.5 * 5.0 = 7.0
        assert abs(lds.career_work - 7.0) < 0.01
        # physical_health = 0.5 * 6.0 + 0.5 * 5.0 = 5.5
        assert abs(lds.physical_health - 5.5) < 0.01
        # finance = 0.5 * 5.0 + 0.5 * 5.0 = 5.0
        assert abs(lds.finance - 5.0) < 0.01

    def test_with_session_id(self, db, user):
        """save_domain_checkin stores session_id."""
        s = JournalSession(
            user_id=user.id,
            started_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
        )
        db.add(s)
        db.flush()

        scores = {
            "career": 5.0, "relationship": 5.0,
            "social": 5.0, "health": 5.0, "finance": 5.0,
        }
        checkin = save_domain_checkin(db, user.id, s.id, scores)
        db.commit()

        assert checkin.session_id == s.id


# ── Domain Check-in History Tests ────────────────────────────────

class TestDomainCheckinHistory:
    def test_returns_correct_order(self, db, user):
        """History returns most recent first."""
        for i in range(3):
            d = (date.today() - timedelta(days=i * 7)).isoformat()
            checkin = DomainCheckin(
                user_id=user.id,
                checkin_date=d,
                career=5.0 + i, relationship=5.0, social=5.0,
                health=5.0, finance=5.0,
                created_at=datetime.utcnow(),
            )
            db.add(checkin)
        db.commit()

        history = get_domain_checkin_history(db, user.id)
        assert len(history) == 3
        # Most recent first
        assert history[0]["checkin_date"] == date.today().isoformat()
        assert history[0]["career"] == 5.0  # i=0

    def test_respects_weeks_param(self, db, user):
        """History only returns check-ins within the specified weeks."""
        # Create one recent and one old
        recent = DomainCheckin(
            user_id=user.id,
            checkin_date=date.today().isoformat(),
            career=7.0, relationship=5.0, social=5.0,
            health=5.0, finance=5.0,
            created_at=datetime.utcnow(),
        )
        old = DomainCheckin(
            user_id=user.id,
            checkin_date=(date.today() - timedelta(weeks=20)).isoformat(),
            career=3.0, relationship=5.0, social=5.0,
            health=5.0, finance=5.0,
            created_at=datetime.utcnow(),
        )
        db.add_all([recent, old])
        db.commit()

        history = get_domain_checkin_history(db, user.id, weeks=12)
        assert len(history) == 1
        assert history[0]["career"] == 7.0

    def test_empty_for_new_user(self, db, user):
        """Empty list for user with no check-ins."""
        history = get_domain_checkin_history(db, user.id)
        assert history == []
