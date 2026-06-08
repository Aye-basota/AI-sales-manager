import uuid
from sqlalchemy import Column, String, Text, Integer, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class TelegramAccount(Base):
    __tablename__ = "telegram_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String(20), nullable=False, unique=True)
    session_string = Column(Text)
    display_name = Column(String(100))
    username = Column(String(32))
    bio = Column(Text)
    avatar_url = Column(Text)
    proxy_url = Column(Text)
    status = Column(String(20), default="warming")
    daily_messages_sent = Column(Integer, default=0)
    last_message_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
