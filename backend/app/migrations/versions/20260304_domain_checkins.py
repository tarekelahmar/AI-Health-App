"""Add domain_checkins table for explicit weekly life domain ratings.

Revision ID: 20260304_domain_checkins
Revises: 20260304_journal_v3_chat
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20260304_domain_checkins"
down_revision = "20260304_journal_v3_chat"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "domain_checkins" not in existing:
        op.create_table(
            "domain_checkins",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("session_id", sa.Integer(), sa.ForeignKey("journal_sessions.id"), nullable=True),
            sa.Column("checkin_date", sa.String(10), nullable=False),
            sa.Column("career", sa.Float(), nullable=False),
            sa.Column("relationship", sa.Float(), nullable=False),
            sa.Column("social", sa.Float(), nullable=False),
            sa.Column("health", sa.Float(), nullable=False),
            sa.Column("finance", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "checkin_date", name="uq_domain_checkin_user_date"),
        )
        op.create_index("ix_domain_checkin_user_date", "domain_checkins", ["user_id", "checkin_date"])


def downgrade() -> None:
    op.drop_index("ix_domain_checkin_user_date", table_name="domain_checkins")
    op.drop_table("domain_checkins")
