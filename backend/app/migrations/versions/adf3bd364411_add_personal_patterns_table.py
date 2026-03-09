"""add_personal_patterns_table

Revision ID: adf3bd364411
Revises: 5370b058d220
Create Date: 2026-03-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'adf3bd364411'
down_revision: Union[str, Sequence[str], None] = '5370b058d220'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create personal_patterns table for Phase 3.2."""
    op.create_table(
        "personal_patterns",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("user_id", sa.Integer, index=True, nullable=False),
        sa.Column("pattern_type", sa.String(30), nullable=False),
        sa.Column("input_signals_json", sa.JSON, nullable=False),
        sa.Column("output_signal", sa.String(100), nullable=False),
        sa.Column("relationship_json", sa.JSON, nullable=True),
        sa.Column("times_observed", sa.Integer, nullable=False, server_default="1"),
        sa.Column("times_confirmed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("current_confidence", sa.Float, nullable=False, server_default="0.3"),
        sa.Column("first_detected", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("last_confirmed", sa.DateTime, nullable=True),
        sa.Column("typical_lag_hours", sa.Float, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="hypothesis"),
        sa.Column("user_acknowledged", sa.Boolean, nullable=False, server_default="0"),
        sa.Column("user_notes", sa.Text, nullable=True),
        sa.Column("source_insight_ids_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_personal_pattern_user_type", "personal_patterns", ["user_id", "pattern_type"])
    op.create_index("ix_personal_pattern_user_status", "personal_patterns", ["user_id", "status"])
    op.create_index("ix_personal_pattern_user_output", "personal_patterns", ["user_id", "output_signal"])


def downgrade() -> None:
    op.drop_index("ix_personal_pattern_user_output", table_name="personal_patterns")
    op.drop_index("ix_personal_pattern_user_status", table_name="personal_patterns")
    op.drop_index("ix_personal_pattern_user_type", table_name="personal_patterns")
    op.drop_table("personal_patterns")
