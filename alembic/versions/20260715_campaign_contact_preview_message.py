"""add campaign contact preview message

Revision ID: 20260715_preview_message
Revises: 20260711_queue_position
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260715_preview_message"
down_revision = "20260711_queue_position"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("campaign_contacts", sa.Column("preview_message", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("campaign_contacts", "preview_message")
