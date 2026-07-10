import uuid
from sqlalchemy import Column, String, BigInteger, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.db.session import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    telegram_username = Column(String(32))
    telegram_user_id = Column(BigInteger)
    phone = Column(String(20))
    first_name = Column(String(100))
    last_name = Column(String(100))
    company_name = Column(String(200))
    position = Column(String(100))
    city = Column(String(100))
    industry = Column(String(100))
    source = Column(String(50), default="csv_import")
    last_source = Column(String(50), default="csv_import")
    source_url = Column(Text)
    source_summary = Column(Text)
    source_message_text = Column(Text)
    source_message_date = Column(String(50))
    is_valid = Column(String(20), default="unknown")
    icp_score = Column(Integer)
    status = Column(String(20), default="new")
    assigned_script_id = Column(UUID(as_uuid=True), ForeignKey("scripts.id"))
    assigned_account_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
