"""Add composite indexes for health_data hot paths

Revision ID: 20251218100000_add_health_data_indexes
Revises: 20251216140000_standardize_metric_type
Create Date: 2025-12-18 10:00:00

Rationale
---------
Query patterns across the engine frequently filter HealthDataPoint by:
    - user_id
    - metric_type
    - timestamp range

Examples:
    - baseline_service.recompute_baseline()
    - signal_builder.fetch_recent_values()
    - metrics.get_metric_series()
    - trust_engine, reconciliation, attribution, drivers

To keep these paths performant at scale, we add composite indexes:
    - ix_health_data_user_metric_ts (user_id, metric_type, timestamp)
    - ix_health_data_user_ts (user_id, timestamp)
"""

from alembic import op
import sqlalchemy as sa


revision = "20251218100000_add_health_data_indexes"
down_revision = "20251216140000_standardize_metric_type"
branch_labels = None
depends_on = None


def upgrade() -> None:
  conn = op.get_bind()
  inspector = sa.inspect(conn)

  if "health_data" not in inspector.get_table_names():
      return

  existing_indexes = {idx["name"] for idx in inspector.get_indexes("health_data")}

  if "ix_health_data_user_metric_ts" not in existing_indexes:
      op.create_index(
          "ix_health_data_user_metric_ts",
          "health_data",
          ["user_id", "metric_type", "timestamp"],
      )

  if "ix_health_data_user_ts" not in existing_indexes:
      op.create_index(
          "ix_health_data_user_ts",
          "health_data",
          ["user_id", "timestamp"],
      )


def downgrade() -> None:
  conn = op.get_bind()
  inspector = sa.inspect(conn)

  if "health_data" not in inspector.get_table_names():
      return

  existing_indexes = {idx["name"] for idx in inspector.get_indexes("health_data")}

  if "ix_health_data_user_metric_ts" in existing_indexes:
      op.drop_index("ix_health_data_user_metric_ts", table_name="health_data")

  if "ix_health_data_user_ts" in existing_indexes:
      op.drop_index("ix_health_data_user_ts", table_name="health_data")


