"""add validity flag to health_data

Phase 1.3: add a nullable boolean validity column to the health_data table.
This is incremental and reversible; existing JSON quality_score payloads are
left untouched.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20251218160000"
down_revision = "20251218100000_add_health_data_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("health_data", sa.Column("validity", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("health_data", "validity")


