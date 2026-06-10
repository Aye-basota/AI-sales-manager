from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class TelegramAccountBase(BaseModel):
    phone: str
    session_string: Optional[str] = None
    display_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    proxy_url: Optional[str] = None
    status: str = "warming"
    daily_messages_sent: int = 0
    last_message_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    last_error: Optional[str] = None


class TelegramAccountCreate(TelegramAccountBase):
    pass


class TelegramAccountUpdate(BaseModel):
    phone: Optional[str] = None
    session_string: Optional[str] = None
    display_name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    proxy_url: Optional[str] = None
    status: Optional[str] = None
    daily_messages_sent: Optional[int] = None
    last_message_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    last_error: Optional[str] = None


class TelegramAccountResponse(TelegramAccountBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
