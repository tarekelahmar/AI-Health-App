"""
Create interventions, protocols, experiments, adherence_events, evaluation_results tables

Revision ID: 20251213180000_create_loop_tables
Revises: 0819a425f7fd
Create Date: 2025-12-13 18:00:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "20251213180000_create_loop_tables"
down_revision = "0819a425f7fd"
branch_labels = None
depends_on = None


def upgrade():
    # Check if tables exist before creating
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if "interventions" not in existing_tables:
        op.create_table(
            "interventions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("intervention_type", sa.String(length=50), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("dose", sa.String(length=100), nullable=True),
            sa.Column("dose_unit", sa.String(length=50), nullable=True),
            sa.Column("schedule", sa.String(length=200), nullable=True),
            sa.Column("timing", sa.String(length=200), nullable=True),
            sa.Column("contraindications", sa.Text(), nullable=True),
            sa.Column("evidence_level", sa.String(length=50), nullable=True),
            sa.Column("citations", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_interventions_user_id", "interventions", ["user_id"])
        op.create_index("ix_interventions_name", "interventions", ["name"])
        op.create_index("ix_interventions_intervention_type", "interventions", ["intervention_type"])
    else:
        # Table exists, check and create missing indexes
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("interventions")]
        if "ix_interventions_user_id" not in existing_indexes:
            op.create_index("ix_interventions_user_id", "interventions", ["user_id"])
        if "ix_interventions_name" not in existing_indexes:
            op.create_index("ix_interventions_name", "interventions", ["name"])
        if "ix_interventions_intervention_type" not in existing_indexes:
            op.create_index("ix_interventions_intervention_type", "interventions", ["intervention_type"])

    if "protocols" not in existing_tables:
        op.create_table(
            "protocols",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("plan_json", sa.Text(), nullable=False),
            sa.Column("stop_rules", sa.Text(), nullable=True),
            sa.Column("monitoring_metrics", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_protocols_user_id", "protocols", ["user_id"])
        op.create_index("ix_protocols_name", "protocols", ["name"])
    else:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("protocols")]
        if "ix_protocols_user_id" not in existing_indexes:
            op.create_index("ix_protocols_user_id", "protocols", ["user_id"])
        if "ix_protocols_name" not in existing_indexes:
            op.create_index("ix_protocols_name", "protocols", ["name"])

    if "experiments" not in existing_tables:
        op.create_table(
            "experiments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("intervention_id", sa.Integer(), nullable=False),
            sa.Column("protocol_id", sa.Integer(), nullable=True),
            sa.Column("hypothesis", sa.Text(), nullable=True),
            sa.Column("primary_metric_key", sa.String(length=100), nullable=False),
            sa.Column("expected_direction", sa.String(length=20), nullable=False),
            sa.Column("baseline_window_days", sa.Integer(), nullable=False, server_default="14"),
            sa.Column("intervention_window_days", sa.Integer(), nullable=False, server_default="14"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("ended_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_experiments_user_id", "experiments", ["user_id"])
        op.create_index("ix_experiments_primary_metric_key", "experiments", ["primary_metric_key"])
    else:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("experiments")]
        if "ix_experiments_user_id" not in existing_indexes:
            op.create_index("ix_experiments_user_id", "experiments", ["user_id"])
        if "ix_experiments_primary_metric_key" not in existing_indexes:
            op.create_index("ix_experiments_primary_metric_key", "experiments", ["primary_metric_key"])

    if "adherence_events" not in existing_tables:
        op.create_table(
            "adherence_events",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("experiment_id", sa.Integer(), nullable=False),
            sa.Column("intervention_id", sa.Integer(), nullable=False),
            sa.Column("taken", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("dose", sa.String(length=100), nullable=True),
            sa.Column("dose_unit", sa.String(length=50), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_adherence_events_experiment_id", "adherence_events", ["experiment_id"])
    else:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("adherence_events")]
        if "ix_adherence_events_experiment_id" not in existing_indexes:
            op.create_index("ix_adherence_events_experiment_id", "adherence_events", ["experiment_id"])

    if "evaluation_results" not in existing_tables:
        op.create_table(
            "evaluation_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("experiment_id", sa.Integer(), nullable=False),
            sa.Column("verdict", sa.String(length=30), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("pre_mean", sa.Float(), nullable=True),
            sa.Column("post_mean", sa.Float(), nullable=True),
            sa.Column("delta", sa.Float(), nullable=True),
            sa.Column("effect_size", sa.Float(), nullable=True),
            sa.Column("data_coverage", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_evaluation_results_experiment_id", "evaluation_results", ["experiment_id"])
    else:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("evaluation_results")]
        if "ix_evaluation_results_experiment_id" not in existing_indexes:
            op.create_index("ix_evaluation_results_experiment_id", "evaluation_results", ["experiment_id"])


def downgrade():
    op.drop_index("ix_evaluation_results_experiment_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    op.drop_index("ix_adherence_events_experiment_id", table_name="adherence_events")
    op.drop_table("adherence_events")
    op.drop_index("ix_experiments_primary_metric_key", table_name="experiments")
    op.drop_index("ix_experiments_user_id", table_name="experiments")
    op.drop_table("experiments")
    op.drop_index("ix_protocols_name", table_name="protocols")
    op.drop_index("ix_protocols_user_id", table_name="protocols")
    op.drop_table("protocols")
    op.drop_index("ix_interventions_intervention_type", table_name="interventions")
    op.drop_index("ix_interventions_name", table_name="interventions")
    op.drop_index("ix_interventions_user_id", table_name="interventions")
    op.drop_table("interventions")
