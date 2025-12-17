"""K3 safety fields on interventions + protocol_json on protocols

Revision ID: k3_safety_fields
Revises: 
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

# NOTE: If you have an existing head revision, set down_revision accordingly.
revision = "k3_safety_fields"
down_revision = "20251214120000"  # Fixed: points to add_safety_fields
branch_labels = None
depends_on = None


def upgrade():
    """
    Canonical K3 safety fields.
    
    NOTE: This migration is idempotent. It only ensures the canonical safety columns
    that are represented in the current domain models exist.
    """
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "interventions" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("interventions")]
        if "safety_risk_level" not in cols:
            op.add_column("interventions", sa.Column("safety_risk_level", sa.String(length=32), nullable=True))
        if "safety_evidence_grade" not in cols:
            op.add_column("interventions", sa.Column("safety_evidence_grade", sa.String(length=8), nullable=True))
        if "safety_boundary" not in cols:
            op.add_column("interventions", sa.Column("safety_boundary", sa.String(length=32), nullable=True))
        if "safety_issues_json" not in cols:
            op.add_column("interventions", sa.Column("safety_issues_json", sa.Text(), nullable=True))
        if "safety_notes" not in cols:
            op.add_column("interventions", sa.Column("safety_notes", sa.Text(), nullable=True))

    if "protocols" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("protocols")]
        if "safety_summary_json" not in cols:
            op.add_column("protocols", sa.Column("safety_summary_json", sa.Text(), nullable=True))


def downgrade():
    # Best-effort drops
    try:
        op.drop_column("protocols", "safety_summary_json")
    except Exception:
        pass
    for col in [
        "safety_notes",
        "safety_issues_json",
        "safety_boundary",
        "safety_evidence_grade",
        "safety_risk_level",
    ]:
        try:
            op.drop_column("interventions", col)
        except Exception:
            pass

