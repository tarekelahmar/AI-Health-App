"""Add safety fields to interventions + protocols

Revision ID: 20251214120000
Revises: <PUT_YOUR_LAST_REVISION_ID_HERE>
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

revision = "20251214120000"
down_revision = "20251213180000_create_loop_tables"  # Fixed: points to loop_tables
branch_labels = None
depends_on = None

def upgrade():
    # Idempotent adds (safe on fresh DB where columns may already exist)
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    if "interventions" in inspector.get_table_names():
        cols = [c["name"] for c in inspector.get_columns("interventions")]
        if "safety_risk_level" not in cols:
            op.add_column("interventions", sa.Column("safety_risk_level", sa.String(), nullable=True))
        if "safety_evidence_grade" not in cols:
            op.add_column("interventions", sa.Column("safety_evidence_grade", sa.String(), nullable=True))
        if "safety_boundary" not in cols:
            op.add_column("interventions", sa.Column("safety_boundary", sa.String(), nullable=True))
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

