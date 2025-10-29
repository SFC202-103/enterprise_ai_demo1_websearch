"""create tracked_selection table

Revision ID: ae12d3f4b1e2
Revises: 5a54d4b84d73
Create Date: 2025-10-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ae12d3f4b1e2'
down_revision = '5a54d4b84d73'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(  # type: ignore
        'tracked_selection',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('match_id', sa.String(), nullable=True),
        sa.Column('team', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('tracked_selection')  # type: ignore
