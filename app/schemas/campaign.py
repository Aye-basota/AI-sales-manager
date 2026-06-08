from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class CampaignBase(BaseModel):
    script_id: Optional[UUID] = None
    name: str
    status: str = "draft"
    total_contacts: int = 0
    processed_contacts: int = 0
    replied_count: int = 0
    qualified_count: int = 0
    meeting_booked_count: int = 0
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
