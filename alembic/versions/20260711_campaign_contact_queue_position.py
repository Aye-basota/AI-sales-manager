"""add campaign contact queue position

Revision ID: 20260711_queue_position
Revises: 20260710_contact_source_context
Create Date: 2026-07-11
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_queue_position"
down_revision = "20260710_contact_source_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "campaign_contacts",
        sa.Column("queue_position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY campaign_id
                    ORDER BY initial_sent_at NULLS FIRST, last_message_at NULLS FIRST, id
                ) AS position
            FROM campaign_contacts
        )
        UPDATE campaign_contacts
        SET queue_position = ranked.position
        FROM ranked
        WHERE campaign_contacts.id = ranked.id
        """
    )
    op.create_index(
        "ix_campaign_contacts_campaign_queue",
        "campaign_contacts",
        ["campaign_id", "queue_position"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_campaign_contacts_campaign_queue",
        table_name="campaign_contacts",
    )
    op.drop_column("campaign_contacts", "queue_position")
