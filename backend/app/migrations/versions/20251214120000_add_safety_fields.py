"""Add safety fields to interventions + protocols

Revision ID: 20251214120000
Revises: <PUT_YOUR_LAST_REVISION_ID_HERE>
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20251214120000"
down_revision = None  # <-- IMPORTANT: set this to your actual latest revision id
branch_labels = None
depends_on = None

def upgrade():
    # interventions
    op.add_column("interventions", sa.Column("safety_risk_level", sa.String(), nullable=True))
    op.add_column("interventions", sa.Column("safety_evidence_grade", sa.String(), nullable=True))
    op.add_column("interventions", sa.Column("safety_boundary", sa.String(), nullable=True))
    op.add_column("interventions", sa.Column("safety_issues_json", sa.Text(), nullable=True))
    op.add_column("interventions", sa.Column("safety_notes", sa.Text(), nullable=True))

    # protocols
    op.add_column("protocols", sa.Column("safety_summary_json", sa.Text(), nullable=True))

def downgrade():
    op.drop_column("protocols", "safety_summary_json")
    op.drop_column("interventions", "safety_notes")
    op.drop_column("interventions", "safety_issues_json")
    op.drop_column("interventions", "safety_boundary")
    op.drop_column("interventions", "safety_evidence_grade")
    op.drop_column("interventions", "safety_risk_level")

