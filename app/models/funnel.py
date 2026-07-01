import uuid
from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class Funnel(Base):
    __tablename__ = "funnels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=True)
    stages = Column(JSON, nullable=False, default=list)
    source_format = Column(String(20), default="json")  # "json" or "text"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
