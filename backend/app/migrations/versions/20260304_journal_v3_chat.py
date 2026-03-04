"""Add Journal V3 chat tables: journal_sessions and journal_messages.

Revision ID: 20260304_journal_v3_chat
Revises: 20260304_phase4
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20260304_journal_v3_chat"
down_revision = "20260304_phase4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    # journal_sessions
    if "journal_sessions" not in existing:
        op.create_table(
            "journal_sessions",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
            sa.Column("daily_score", sa.Float(), nullable=True),
            sa.Column("score_confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_journal_sessions_user_id", "journal_sessions", ["user_id"])

    # journal_messages
    if "journal_messages" not in existing:
        op.create_table(
            "journal_messages",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("journal_sessions.id"), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("ai_analysis_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_journal_messages_session_id", "journal_messages", ["session_id"])
        op.create_index("ix_journal_messages_user_id", "journal_messages", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_journal_messages_user_id", table_name="journal_messages")
    op.drop_index("ix_journal_messages_session_id", table_name="journal_messages")
    op.drop_table("journal_messages")
    op.drop_index("ix_journal_sessions_user_id", table_name="journal_sessions")
    op.drop_table("journal_sessions")
