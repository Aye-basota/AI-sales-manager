from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class FunnelStage(BaseModel):
    stage: str
    goal: Optional[str] = None
    instructions: Optional[str] = None
    max_length: Optional[int] = None
    allow_call_to_action: Optional[bool] = None


class FunnelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    campaign_id: Optional[UUID] = None
    stages: List[FunnelStage]
    source_format: str = "json"
    notes: Optional[str] = None


class FunnelCreate(FunnelBase):
    pass


class FunnelResponse(FunnelBase):
    id: UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FunnelPreviewRequest(BaseModel):
    content: str
    format: str = "json"  # "json" or "text"
    name: Optional[str] = "Preview Funnel"


class FunnelUploadRequest(BaseModel):
    content: str
    format: str = "json"  # "json" or "text"
    name: str = Field(..., min_length=1, max_length=100)
    campaign_id: Optional[UUID] = None
    notes: Optional[str] = None
    force: bool = False  # allow overwriting an active funnel when True


class FunnelParseError(BaseModel):
    detail: str
