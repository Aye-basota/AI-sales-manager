"""Add funnels table and automation tracking fields for MVP v2

Revision ID: 20260630_mvp_v2_funnel_and_automation
Revises: 20260615_funnel_fields
Create Date: 2026-06-30 20:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20260630_mvp_v2_funnel_and_automation'
down_revision: Union[str, None] = '20260615_funnel_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create funnels table for TECH-04/TECH-05
    op.create_table(
        'funnels',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('stages', sa.JSON(), nullable=False),
        sa.Column('source_format', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Add was_escalated field to conversations for TECH-06
    op.add_column('conversations', sa.Column('was_escalated', sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column('conversations', 'was_escalated')
    op.drop_table('funnels')
