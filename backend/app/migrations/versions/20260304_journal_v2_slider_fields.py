"""Add V2 journal slider fields and AI companion columns to daily_checkins.

Phase 1A of Journal Companion feature:
- New V2 sliders: overall_wellbeing, connection (Float)
- Change energy/mood/focus from Integer to Float (backward compat)
- AI companion fields: ai_inferred_json, context_tags_json,
  ai_response_text, discrepancy_json, milestone_json
- Entry metadata: word_count, depth_level

Revision ID: 20260304_journal_v2
Revises: adf3bd364411
Create Date: 2026-03-04
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260304_journal_v2"
down_revision = "adf3bd364411"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -- New V2 slider columns --
    op.add_column("daily_checkins", sa.Column("overall_wellbeing", sa.Float(), nullable=True))
    op.add_column("daily_checkins", sa.Column("connection", sa.Float(), nullable=True))

    # -- Change energy/mood/focus from Integer to Float --
    # SQLite doesn't support ALTER COLUMN, but PostgreSQL does.
    # For SQLite (tests), the existing Integer columns already accept floats.
    # For PostgreSQL (production), we alter the type.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "daily_checkins", "energy",
            type_=sa.Float(),
            existing_type=sa.Integer(),
            existing_nullable=True,
        )
        op.alter_column(
            "daily_checkins", "mood",
            type_=sa.Float(),
            existing_type=sa.Integer(),
            existing_nullable=True,
        )
        op.alter_column(
            "daily_checkins", "focus",
            type_=sa.Float(),
            existing_type=sa.Integer(),
            existing_nullable=True,
        )

    # -- AI companion fields (Phase 2 will populate these) --
    op.add_column("daily_checkins", sa.Column("ai_inferred_json", sa.JSON(), nullable=True))
    op.add_column("daily_checkins", sa.Column("context_tags_json", sa.JSON(), nullable=True))
    op.add_column("daily_checkins", sa.Column("ai_response_text", sa.String(), nullable=True))
    op.add_column("daily_checkins", sa.Column("discrepancy_json", sa.JSON(), nullable=True))
    op.add_column("daily_checkins", sa.Column("milestone_json", sa.JSON(), nullable=True))

    # -- Entry metadata --
    op.add_column("daily_checkins", sa.Column("word_count", sa.Integer(), nullable=True))
    op.add_column("daily_checkins", sa.Column("depth_level", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("daily_checkins", "depth_level")
    op.drop_column("daily_checkins", "word_count")
    op.drop_column("daily_checkins", "milestone_json")
    op.drop_column("daily_checkins", "discrepancy_json")
    op.drop_column("daily_checkins", "ai_response_text")
    op.drop_column("daily_checkins", "context_tags_json")
    op.drop_column("daily_checkins", "ai_inferred_json")

    # Revert Float -> Integer for energy/mood/focus
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "daily_checkins", "focus",
            type_=sa.Integer(),
            existing_type=sa.Float(),
            existing_nullable=True,
        )
        op.alter_column(
            "daily_checkins", "mood",
            type_=sa.Integer(),
            existing_type=sa.Float(),
            existing_nullable=True,
        )
        op.alter_column(
            "daily_checkins", "energy",
            type_=sa.Integer(),
            existing_type=sa.Float(),
            existing_nullable=True,
        )

    op.drop_column("daily_checkins", "connection")
    op.drop_column("daily_checkins", "overall_wellbeing")
