"""add business and owner clarification fields

Revision ID: 20260719_business_clarifications
Revises: 20260715_preview_message
Create Date: 2026-07-19
"""

from alembic import op
import sqlalchemy as sa


revision = "20260719_business_clarifications"
down_revision = "20260715_preview_message"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("scripts", sa.Column("business_details", sa.JSON(), nullable=True))
    op.add_column(
        "scripts",
        sa.Column(
            "owner_clarification_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.add_column(
        "conversations",
        sa.Column("owner_clarification", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversations", "owner_clarification")
    op.drop_column("scripts", "owner_clarification_enabled")
    op.drop_column("scripts", "business_details")
