"""add contact source context fields

Revision ID: 20260710_contact_source_context
Revises: 20260630_mvp_v2
Create Date: 2026-07-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260710_contact_source_context"
down_revision = "20260630_mvp_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("contacts", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("contacts", sa.Column("source_summary", sa.Text(), nullable=True))
    op.add_column("contacts", sa.Column("source_message_text", sa.Text(), nullable=True))
    op.add_column("contacts", sa.Column("source_message_date", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("contacts", "source_message_date")
    op.drop_column("contacts", "source_message_text")
    op.drop_column("contacts", "source_summary")
    op.drop_column("contacts", "source_url")
