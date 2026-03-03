"""Add robust baseline fields to baselines table

Revision ID: b1732254f4a8
Revises: 20251218160000
Create Date: 2026-03-03 09:18:28.086816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b1732254f4a8'
down_revision: Union[str, Sequence[str], None] = '20251218160000'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Phase 2.1 robust baseline columns."""
    op.add_column('baselines', sa.Column('method', sa.String(), nullable=True))
    op.add_column('baselines', sa.Column('n_samples', sa.Integer(), nullable=True))
    op.add_column('baselines', sa.Column('ci_80_low', sa.Float(), nullable=True))
    op.add_column('baselines', sa.Column('ci_80_high', sa.Float(), nullable=True))
    op.add_column('baselines', sa.Column('ci_95_low', sa.Float(), nullable=True))
    op.add_column('baselines', sa.Column('ci_95_high', sa.Float(), nullable=True))
    op.add_column('baselines', sa.Column('is_stable', sa.Boolean(), nullable=True))

    # Backfill existing rows with legacy method
    op.execute("UPDATE baselines SET method = 'mean_std' WHERE method IS NULL")


def downgrade() -> None:
    """Remove Phase 2.1 robust baseline columns."""
    op.drop_column('baselines', 'is_stable')
    op.drop_column('baselines', 'ci_95_high')
    op.drop_column('baselines', 'ci_95_low')
    op.drop_column('baselines', 'ci_80_high')
    op.drop_column('baselines', 'ci_80_low')
    op.drop_column('baselines', 'n_samples')
    op.drop_column('baselines', 'method')
