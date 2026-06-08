import uuid
from sqlalchemy import Column, String, Text, Integer, Time, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class Script(Base):
    __tablename__ = "scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    role_prompt = Column(Text, nullable=False)
    target_audience = Column(Text)
    goal = Column(Text, nullable=False)
    success_criteria = Column(Text)
    tone = Column(String(20), default="professional")
    max_messages = Column(Integer, default=2)
    follow_up_delay_hours = Column(Integer, default=24)
    working_hours_start = Column(Time, default="09:00")
    working_hours_end = Column(Time, default="18:00")
    timezone = Column(String(50), default="Europe/Moscow")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
