from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ConversationBase(BaseModel):
    contact_id: Optional[UUID] = None
    campaign_id: Optional[UUID] = None
    current_state: str = "cold"
    sentiment: Optional[str] = None
    facts_extracted: Dict[str, Any] = {}
    operator_status: Optional[str] = None
    operator_notes: Optional[str] = None
    last_message_at: Optional[datetime] = None


class ConversationUpdateStatus(BaseModel):
    operator_status: str
    operator_notes: Optional[str] = None


class ConversationResponse(ConversationBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: UUID
    conversation_id: Optional[UUID] = None
    direction: Optional[str] = None
    content: str
    message_type: str = "text"
    intent_classification: Optional[str] = None
    llm_model: Optional[str] = None
    tokens_used: Optional[int] = None
    typing_delay_ms: Optional[int] = None
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)
