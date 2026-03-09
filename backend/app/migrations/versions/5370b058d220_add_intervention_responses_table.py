"""add_intervention_responses_table

Revision ID: 5370b058d220
Revises: b1732254f4a8
Create Date: 2026-03-03 09:35:59.986697

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5370b058d220'
down_revision: Union[str, Sequence[str], None] = 'b1732254f4a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create intervention_responses table for Phase 3.1."""
    op.create_table(
        "intervention_responses",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, index=True, nullable=False),
        sa.Column("intervention_id", sa.Integer, index=True, nullable=False),
        sa.Column("intervention_key", sa.String(100), index=True, nullable=False),
        sa.Column("experiment_id", sa.Integer, nullable=True),
        sa.Column("start_date", sa.DateTime, nullable=False),
        sa.Column("end_date", sa.DateTime, nullable=True),
        sa.Column("duration_days", sa.Integer, nullable=True),
        sa.Column("target_metrics_json", sa.JSON, nullable=True),
        sa.Column("verdict", sa.String(30), nullable=False),
        sa.Column("overall_effect_size", sa.Float, nullable=True),
        sa.Column("overall_confidence", sa.Float, nullable=True),
        sa.Column("confounders_json", sa.JSON, nullable=True),
        sa.Column("regime_during", sa.String(50), nullable=True),
        sa.Column("user_perceived_benefit", sa.Integer, nullable=True),
        sa.Column("user_notes", sa.Text, nullable=True),
        sa.Column("would_recommend", sa.Integer, nullable=True),
        sa.Column("adherence_rate", sa.Float, nullable=True),
        sa.Column("evaluation_ids_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_intervention_response_user_key",
        "intervention_responses",
        ["user_id", "intervention_key"],
    )
    op.create_index(
        "ix_intervention_response_user_verdict",
        "intervention_responses",
        ["user_id", "verdict"],
    )


def downgrade() -> None:
    """Drop intervention_responses table."""
    op.drop_index("ix_intervention_response_user_verdict", table_name="intervention_responses")
    op.drop_index("ix_intervention_response_user_key", table_name="intervention_responses")
    op.drop_table("intervention_responses")
