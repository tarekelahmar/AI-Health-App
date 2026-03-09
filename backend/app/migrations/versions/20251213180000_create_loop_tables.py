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
            sa.Column("key", sa.String(length=128), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("category", sa.String(length=100), nullable=True),
            sa.Column("dosage", sa.String(length=200), nullable=True),
            sa.Column("schedule", sa.String(length=200), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            # Safety fields (canonical)
            sa.Column("safety_risk_level", sa.String(length=32), nullable=True),
            sa.Column("safety_evidence_grade", sa.String(length=8), nullable=True),
            sa.Column("safety_boundary", sa.String(length=32), nullable=True),
            sa.Column("safety_issues_json", sa.Text(), nullable=True),
            sa.Column("safety_notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_interventions_user_id", "interventions", ["user_id"])
        op.create_index("ix_interventions_name", "interventions", ["name"])
        op.create_index("ix_interventions_key", "interventions", ["key"])
    else:
        # Table exists, check and create missing indexes
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("interventions")]
        if "ix_interventions_user_id" not in existing_indexes:
            op.create_index("ix_interventions_user_id", "interventions", ["user_id"])
        if "ix_interventions_name" not in existing_indexes:
            op.create_index("ix_interventions_name", "interventions", ["name"])
        if "ix_interventions_key" not in existing_indexes:
            op.create_index("ix_interventions_key", "interventions", ["key"])

    if "protocols" not in existing_tables:
        op.create_table(
            "protocols",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("interventions_json", sa.Text(), nullable=True),
            sa.Column("safety_summary_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_protocols_user_id", "protocols", ["user_id"])
        op.create_index("ix_protocols_title", "protocols", ["title"])
    else:
        # Table exists in initial schema; evolve it to current shape (idempotent)
        existing_cols = [c["name"] for c in inspector.get_columns("protocols")]
        if "title" not in existing_cols:
            op.add_column("protocols", sa.Column("title", sa.String(length=200), nullable=True))
        if "description" not in existing_cols:
            op.add_column("protocols", sa.Column("description", sa.Text(), nullable=True))
        if "version" not in existing_cols:
            op.add_column("protocols", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        if "interventions_json" not in existing_cols:
            op.add_column("protocols", sa.Column("interventions_json", sa.Text(), nullable=True))
        if "safety_summary_json" not in existing_cols:
            op.add_column("protocols", sa.Column("safety_summary_json", sa.Text(), nullable=True))
        if "updated_at" not in existing_cols:
            op.add_column("protocols", sa.Column("updated_at", sa.DateTime(), nullable=True))

        existing_indexes = [idx['name'] for idx in inspector.get_indexes("protocols")]
        if "ix_protocols_user_id" not in existing_indexes:
            op.create_index("ix_protocols_user_id", "protocols", ["user_id"])
        if "ix_protocols_title" not in existing_indexes:
            op.create_index("ix_protocols_title", "protocols", ["title"])

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
        op.create_index("ix_experiments_intervention_id", "experiments", ["intervention_id"])
        op.create_index("ix_experiments_protocol_id", "experiments", ["protocol_id"])
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
        op.create_index("ix_adherence_events_user_id", "adherence_events", ["user_id"])
    else:
        existing_indexes = [idx['name'] for idx in inspector.get_indexes("adherence_events")]
        if "ix_adherence_events_experiment_id" not in existing_indexes:
            op.create_index("ix_adherence_events_experiment_id", "adherence_events", ["experiment_id"])
        if "ix_adherence_events_user_id" not in existing_indexes:
            op.create_index("ix_adherence_events_user_id", "adherence_events", ["user_id"])

    if "evaluation_results" not in existing_tables:
        op.create_table(
            "evaluation_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("experiment_id", sa.Integer(), nullable=False),
            sa.Column("verdict", sa.String(length=30), nullable=False),
            sa.Column("metric_key", sa.String(length=100), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("baseline_mean", sa.Float(), nullable=False),
            sa.Column("baseline_std", sa.Float(), nullable=False),
            sa.Column("intervention_mean", sa.Float(), nullable=False),
            sa.Column("intervention_std", sa.Float(), nullable=False),
            sa.Column("delta", sa.Float(), nullable=False),
            sa.Column("percent_change", sa.Float(), nullable=False),
            sa.Column("effect_size", sa.Float(), nullable=False),
            sa.Column("coverage", sa.Float(), nullable=False),
            sa.Column("adherence_rate", sa.Float(), nullable=False),
            sa.Column("details_json", sa.JSON(), nullable=True),
            # legacy columns (nullable)
            sa.Column("pre_mean", sa.Float(), nullable=True),
            sa.Column("post_mean", sa.Float(), nullable=True),
            sa.Column("data_coverage", sa.Float(), nullable=True),
            sa.Column("confidence", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_evaluation_results_experiment_id", "evaluation_results", ["experiment_id"])
        op.create_index("ix_evaluation_results_user_id", "evaluation_results", ["user_id"])
        op.create_index("ix_evaluation_results_metric_key", "evaluation_results", ["metric_key"])
    else:
        existing_indexes = [idx["name"] for idx in inspector.get_indexes("evaluation_results")]
        existing_cols = [c["name"] for c in inspector.get_columns("evaluation_results")]

        if "ix_evaluation_results_experiment_id" not in existing_indexes:
            op.create_index("ix_evaluation_results_experiment_id", "evaluation_results", ["experiment_id"])

        if "ix_evaluation_results_user_id" not in existing_indexes:
            op.create_index("ix_evaluation_results_user_id", "evaluation_results", ["user_id"])

        # SCHEMA GOVERNANCE: Some legacy databases may have evaluation_results without metric_key.
        # To avoid migration failure and to support new query patterns, add the column if missing
        # and only then create the composite index.
        if "metric_key" not in existing_cols:
            op.add_column("evaluation_results", sa.Column("metric_key", sa.String(length=100), nullable=True))

        if "ix_evaluation_results_metric_key" not in existing_indexes and "metric_key" in existing_cols + ["metric_key"]:
            op.create_index("ix_evaluation_results_metric_key", "evaluation_results", ["metric_key"])


def downgrade():
    try:
        op.drop_index("ix_evaluation_results_metric_key", table_name="evaluation_results")
    except Exception:
        pass
    try:
        op.drop_index("ix_evaluation_results_user_id", table_name="evaluation_results")
    except Exception:
        pass
    op.drop_index("ix_evaluation_results_experiment_id", table_name="evaluation_results")
    op.drop_table("evaluation_results")
    try:
        op.drop_index("ix_adherence_events_user_id", table_name="adherence_events")
    except Exception:
        pass
    op.drop_index("ix_adherence_events_experiment_id", table_name="adherence_events")
    op.drop_table("adherence_events")
    op.drop_index("ix_experiments_primary_metric_key", table_name="experiments")
    try:
        op.drop_index("ix_experiments_protocol_id", table_name="experiments")
    except Exception:
        pass
    try:
        op.drop_index("ix_experiments_intervention_id", table_name="experiments")
    except Exception:
        pass
    op.drop_index("ix_experiments_user_id", table_name="experiments")
    op.drop_table("experiments")
    op.drop_index("ix_protocols_title", table_name="protocols")
    op.drop_index("ix_protocols_user_id", table_name="protocols")
    op.drop_table("protocols")
    try:
        op.drop_index("ix_interventions_key", table_name="interventions")
    except Exception:
        pass
    op.drop_index("ix_interventions_name", table_name="interventions")
    op.drop_index("ix_interventions_user_id", table_name="interventions")
    op.drop_table("interventions")
