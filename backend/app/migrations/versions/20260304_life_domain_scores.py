"""Add life_domain_scores table.

Revision ID: 20260304_life_domains
Revises: 20260304_journal_v2
Create Date: 2026-03-04
"""
from alembic import op
import sqlalchemy as sa


revision = "20260304_life_domains"
down_revision = "20260304_journal_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use IF NOT EXISTS to handle case where table was already created
    # by SQLAlchemy's create_all (e.g., during development)
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "life_domain_scores" in inspector.get_table_names():
        return  # Table already exists, skip creation

    op.create_table(
        "life_domain_scores",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("score_date", sa.String(10), nullable=False),
        sa.Column("career_work", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("relationship", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("physical_health", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("mental_emotional", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("social_friendships", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("purpose_meaning", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("finance", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("structure_routine", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("growth_learning", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("hobbies_play", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("derivation_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "score_date", name="uq_life_domain_user_date"),
    )
    op.create_index("ix_life_domain_scores_user_date", "life_domain_scores", ["user_id", "score_date"])


def downgrade() -> None:
    op.drop_index("ix_life_domain_scores_user_date", table_name="life_domain_scores")
    op.drop_table("life_domain_scores")
