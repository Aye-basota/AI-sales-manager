import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contact_id = Column(UUID(as_uuid=True), ForeignKey("contacts.id"))
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"))
    current_state = Column(String(20), default="cold")
    sentiment = Column(String(20))
    facts_extracted = Column(JSON, default={})
    operator_status = Column(String(20))
    operator_notes = Column(Text)
    last_message_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"))
    direction = Column(String(10))
    content = Column(Text, nullable=False)
    message_type = Column(String(20), default="text")
    intent_classification = Column(String(50))
    llm_model = Column(String(50))
    tokens_used = Column(Integer)
    typing_delay_ms = Column(Integer)
    sent_at = Column(DateTime(timezone=True), server_default=func.now())
