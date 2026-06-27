import uuid
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"))
    name = Column(String(100), nullable=False)
    status = Column(String(20), default="draft")
    total_contacts = Column(Integer, default=0)
    processed_contacts = Column(Integer, default=0)
    replied_count = Column(Integer, default=0)
    qualified_count = Column(Integer, default=0)
    meeting_booked_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CampaignContact(Base):
    __tablename__ = "campaign_contacts"

    __table_args__ = (UniqueConstraint("campaign_id", "contact_id"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"))
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    status = Column(String(20), default="pending")
    initial_sent_at = Column(DateTime(timezone=True))
    follow_up_sent_at = Column(DateTime(timezone=True))
    reply_received_at = Column(DateTime(timezone=True))
    last_message_at = Column(DateTime(timezone=True))
    message_count = Column(Integer, default=0)
