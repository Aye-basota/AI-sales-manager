from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CampaignBase(BaseModel):
    script_id: Optional[UUID] = None
    name: str
    status: str = "draft"
    total_contacts: int = 0
    processed_contacts: Optional[int] = 0
    replied_count: Optional[int] = 0
    qualified_count: Optional[int] = 0
    meeting_booked_count: Optional[int] = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdateStatus(BaseModel):
    status: str


class CampaignResponse(CampaignBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CampaignAddContacts(BaseModel):
    contact_ids: List[UUID]


class CampaignContactResponse(BaseModel):
    id: UUID
    campaign_id: UUID
    contact_id: UUID
    status: str = "pending"
    initial_sent_at: Optional[datetime] = None
    follow_up_sent_at: Optional[datetime] = None
    reply_received_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    message_count: Optional[int] = None
    queue_position: int = 0
    preview_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CampaignContactListItem(BaseModel):
    contact_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    telegram_username: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    source: str = "csv_import"
    icp_score: Optional[int] = None
    contact_status: str = "new"
    status: str
    initial_sent_at: Optional[datetime] = None
    follow_up_sent_at: Optional[datetime] = None
    reply_received_at: Optional[datetime] = None
    last_message_at: Optional[datetime] = None
    message_count: Optional[int] = None
    queue_position: int = 0
    preview_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
