"""Add Phase 4 tables: user_preferences and milestones.

Revision ID: 20260304_phase4
Revises: 20260304_life_domains
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20260304_phase4"
down_revision = "20260304_life_domains"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # user_preferences
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = inspector.get_table_names()

    if "user_preferences" not in existing:
        op.create_table(
            "user_preferences",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
            sa.Column("preferred_depth_level", sa.Integer(), nullable=False, server_default="2"),
            sa.Column("journal_onboarded", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )

    # milestones
    if "milestones" not in existing:
        op.create_table(
            "milestones",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("milestone_type", sa.String(), nullable=False),
            sa.Column("detected_date", sa.Date(), nullable=False),
            sa.Column("description", sa.String(), nullable=False),
            sa.Column("category", sa.String(), nullable=False),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("user_id", "milestone_type", "detected_date",
                                name="uq_milestones_user_type_date"),
        )
        op.create_index("ix_milestones_user_date", "milestones", ["user_id", "detected_date"])


def downgrade() -> None:
    op.drop_index("ix_milestones_user_date", table_name="milestones")
    op.drop_table("milestones")
    op.drop_table("user_preferences")
