"""K3 safety fields on interventions + protocol_json on protocols

Revision ID: k3_safety_fields
Revises: 
Create Date: 2025-12-14
"""

from alembic import op
import sqlalchemy as sa

# NOTE: If you have an existing head revision, set down_revision accordingly.
revision = "k3_safety_fields"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # interventions: add safety columns if missing
    # Use batch_alter_table if supported, otherwise try direct alter
    try:
        with op.batch_alter_table("interventions") as batch:
            try:
                batch.add_column(sa.Column("intervention_key", sa.String(length=128), nullable=True))
            except Exception:
                pass  # Column may already exist
            try:
                batch.add_column(sa.Column("safety_risk_level", sa.String(length=32), nullable=True))
            except Exception:
                pass
            try:
                batch.add_column(sa.Column("safety_evidence_grade", sa.String(length=8), nullable=True))
            except Exception:
                pass
            try:
                batch.add_column(sa.Column("safety_boundary", sa.String(length=32), nullable=True))
            except Exception:
                pass
            try:
                batch.add_column(sa.Column("safety_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")))
            except Exception:
                pass
            try:
                batch.add_column(sa.Column("safety_json", sa.Text(), nullable=True))
            except Exception:
                pass
    except Exception:
        # Fallback: direct alter if batch not supported
        try:
            op.add_column("interventions", sa.Column("intervention_key", sa.String(length=128), nullable=True))
        except Exception:
            pass
        try:
            op.add_column("interventions", sa.Column("safety_risk_level", sa.String(length=32), nullable=True))
        except Exception:
            pass
        try:
            op.add_column("interventions", sa.Column("safety_evidence_grade", sa.String(length=8), nullable=True))
        except Exception:
            pass
        try:
            op.add_column("interventions", sa.Column("safety_boundary", sa.String(length=32), nullable=True))
        except Exception:
            pass
        try:
            op.add_column("interventions", sa.Column("safety_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")))
        except Exception:
            pass
        try:
            op.add_column("interventions", sa.Column("safety_json", sa.Text(), nullable=True))
        except Exception:
            pass

    # protocols: ensure protocol_json exists
    try:
        with op.batch_alter_table("protocols") as batch:
            try:
                batch.add_column(sa.Column("protocol_json", sa.Text(), nullable=True))
            except Exception:
                pass
    except Exception:
        try:
            op.add_column("protocols", sa.Column("protocol_json", sa.Text(), nullable=True))
        except Exception:
            pass


def downgrade():
    try:
        with op.batch_alter_table("protocols") as batch:
            try:
                batch.drop_column("protocol_json")
            except Exception:
                pass
    except Exception:
        try:
            op.drop_column("protocols", "protocol_json")
        except Exception:
            pass

    try:
        with op.batch_alter_table("interventions") as batch:
            try:
                batch.drop_column("safety_json")
            except Exception:
                pass
            try:
                batch.drop_column("safety_blocked")
            except Exception:
                pass
            try:
                batch.drop_column("safety_boundary")
            except Exception:
                pass
            try:
                batch.drop_column("safety_evidence_grade")
            except Exception:
                pass
            try:
                batch.drop_column("safety_risk_level")
            except Exception:
                pass
            try:
                batch.drop_column("intervention_key")
            except Exception:
                pass
    except Exception:
        try:
            op.drop_column("interventions", "safety_json")
        except Exception:
            pass
        try:
            op.drop_column("interventions", "safety_blocked")
        except Exception:
            pass
        try:
            op.drop_column("interventions", "safety_boundary")
        except Exception:
            pass
        try:
            op.drop_column("interventions", "safety_evidence_grade")
        except Exception:
            pass
        try:
            op.drop_column("interventions", "safety_risk_level")
        except Exception:
            pass
        try:
            op.drop_column("interventions", "intervention_key")
        except Exception:
            pass

