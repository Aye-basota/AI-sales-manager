from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ContactBase(BaseModel):
    telegram_username: Optional[str] = None
    telegram_user_id: Optional[int] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    source: str = "csv_import"
    last_source: Optional[str] = None
    source_url: Optional[str] = None
    source_summary: Optional[str] = None
    source_message_text: Optional[str] = None
    source_message_date: Optional[str] = None
    is_valid: Optional[str] = "unknown"
    icp_score: Optional[int] = None
    status: str = "new"
    assigned_script_id: Optional[UUID] = None
    assigned_account_id: Optional[UUID] = None


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    telegram_username: Optional[str] = None
    telegram_user_id: Optional[int] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_name: Optional[str] = None
    position: Optional[str] = None
    city: Optional[str] = None
    industry: Optional[str] = None
    source: Optional[str] = None
    last_source: Optional[str] = None
    source_url: Optional[str] = None
    source_summary: Optional[str] = None
    source_message_text: Optional[str] = None
    source_message_date: Optional[str] = None
    is_valid: Optional[str] = None
    icp_score: Optional[int] = None
    status: Optional[str] = None
    assigned_script_id: Optional[UUID] = None
    assigned_account_id: Optional[UUID] = None


class ContactResponse(ContactBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
