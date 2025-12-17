"""Merge safety fields migrations into single linear chain

Revision ID: 20251216130000_merge_safety_fields
Revises: 20251213180000_create_loop_tables
Create Date: 2025-12-16 13:00:00

This migration consolidates the safety field additions from:
- 20251214120000_add_safety_fields
- k3_safety_fields

And ensures all safety fields are present in a single migration.
"""

from alembic import op
import sqlalchemy as sa

revision = "20251216130000_merge_safety_fields"
down_revision = "k3_safety_fields"  # Points to the last safety migration
branch_labels = None
depends_on = None


def upgrade():
    """
    Add all safety fields to interventions and protocols.
    Uses IF NOT EXISTS pattern to be idempotent.
    """
    # Check if columns exist before adding (idempotent)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # Interventions safety fields
    interventions_columns = [col['name'] for col in inspector.get_columns('interventions')] if 'interventions' in inspector.get_table_names() else []
    
    if 'safety_risk_level' not in interventions_columns:
        op.add_column('interventions', sa.Column('safety_risk_level', sa.String(length=32), nullable=True))
    
    if 'safety_evidence_grade' not in interventions_columns:
        op.add_column('interventions', sa.Column('safety_evidence_grade', sa.String(length=8), nullable=True))
    
    if 'safety_boundary' not in interventions_columns:
        op.add_column('interventions', sa.Column('safety_boundary', sa.String(length=32), nullable=True))
    
    if 'safety_issues_json' not in interventions_columns:
        op.add_column('interventions', sa.Column('safety_issues_json', sa.Text(), nullable=True))
    
    if 'safety_notes' not in interventions_columns:
        op.add_column('interventions', sa.Column('safety_notes', sa.Text(), nullable=True))
    
    # Protocols safety fields
    protocols_columns = [col['name'] for col in inspector.get_columns('protocols')] if 'protocols' in inspector.get_table_names() else []
    
    if 'safety_summary_json' not in protocols_columns:
        op.add_column('protocols', sa.Column('safety_summary_json', sa.Text(), nullable=True))


def downgrade():
    """Remove safety fields"""
    try:
        op.drop_column('protocols', 'safety_summary_json')
    except Exception:
        pass
    
    try:
        op.drop_column('interventions', 'safety_notes')
        op.drop_column('interventions', 'safety_issues_json')
        op.drop_column('interventions', 'safety_boundary')
        op.drop_column('interventions', 'safety_evidence_grade')
        op.drop_column('interventions', 'safety_risk_level')
    except Exception:
        pass

