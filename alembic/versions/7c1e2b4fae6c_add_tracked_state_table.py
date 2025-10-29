"""create tracked_state table

Revision ID: 7c1e2b4fae6c
Revises: ae12d3f4b1e2
Create Date: 2025-10-28 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7c1e2b4fae6c'
down_revision = 'ae12d3f4b1e2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(  # type: ignore
        'tracked_state',
        sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
        sa.Column('match_id', sa.String(), nullable=False),
        sa.Column('home', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('away', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('round', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_run', sa.String(), nullable=True),
        sa.Column('leader_pid', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_table('tracked_state')  # type: ignore
