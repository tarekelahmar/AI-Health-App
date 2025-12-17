"""Standardize metric_type field name

Revision ID: 20251216140000_standardize_metric_type
Revises: 20251216130000_merge_safety_fields
Create Date: 2025-12-16 14:00:00

SCHEMA GOVERNANCE: Canonical field semantics enforcement.
Renames 'data_type' column to 'metric_type' in health_data table
to match the canonical naming used in other tables (baselines, wearable_samples).
"""

from alembic import op
import sqlalchemy as sa

revision = "20251216140000_standardize_metric_type"
down_revision = "20251216130000_merge_safety_fields"
branch_labels = None
depends_on = None


def upgrade():
    """
    Rename data_type to metric_type in health_data table.
    This enforces canonical field semantics across all tables.
    """
    # Check if column exists before renaming
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'health_data' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('health_data')]
        
        # If data_type exists and metric_type doesn't, rename it
        if 'data_type' in columns and 'metric_type' not in columns:
            op.alter_column('health_data', 'data_type', new_column_name='metric_type')
        elif 'data_type' in columns and 'metric_type' in columns:
            # Both exist - drop data_type (assuming metric_type is the canonical)
            op.drop_column('health_data', 'data_type')
        # If only metric_type exists, do nothing (already canonical)


def downgrade():
    """
    Revert to data_type (for rollback scenarios).
    Note: This may cause issues if code expects metric_type.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'health_data' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('health_data')]
        
        if 'metric_type' in columns and 'data_type' not in columns:
            op.alter_column('health_data', 'metric_type', new_column_name='data_type')

