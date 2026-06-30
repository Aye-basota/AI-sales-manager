from datetime import time, datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class ScriptBase(BaseModel):
    name: str
    role_prompt: str
    target_audience: Optional[str] = None
    goal: str
    success_criteria: Optional[str] = None
    tone: str = "professional"
    max_messages: int = 2
    follow_up_delay_hours: int = 24
    working_hours_start: time
    working_hours_end: time
    timezone: str = "Europe/Moscow"
    is_active: bool = True

    # Sales funnel configuration
    sales_funnel: Optional[List[Any]] = None
    first_message_goal: str = "trust"
    call_to_action: str = "15-минутный созвон"
    language: str = "ru"
    emoji_policy: str = "forbidden"
    max_first_message_length: int = 200


class ScriptCreate(ScriptBase):
    pass


class ScriptUpdate(BaseModel):
    name: Optional[str] = None
    role_prompt: Optional[str] = None
    target_audience: Optional[str] = None
    goal: Optional[str] = None
    success_criteria: Optional[str] = None
    tone: Optional[str] = None
    max_messages: Optional[int] = None
    follow_up_delay_hours: Optional[int] = None
    working_hours_start: Optional[time] = None
    working_hours_end: Optional[time] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None

    sales_funnel: Optional[List[Any]] = None
    first_message_goal: Optional[str] = None
    call_to_action: Optional[str] = None
    language: Optional[str] = None
    emoji_policy: Optional[str] = None
    max_first_message_length: Optional[int] = None


class ScriptResponse(ScriptBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
