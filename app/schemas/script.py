from datetime import time, datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    business_details: dict[str, Any] = Field(default_factory=dict)
    owner_clarification_enabled: bool = True

    @field_validator("sales_funnel", mode="before")
    @classmethod
    def normalize_sales_funnel(cls, value):
        if value == {}:
            return []
        return value

    @field_validator("first_message_goal", mode="before")
    @classmethod
    def default_first_message_goal(cls, value):
        return value or "trust"

    @field_validator("call_to_action", mode="before")
    @classmethod
    def default_call_to_action(cls, value):
        return value or "15-минутный созвон"

    @field_validator("language", mode="before")
    @classmethod
    def default_language(cls, value):
        return value or "ru"

    @field_validator("emoji_policy", mode="before")
    @classmethod
    def default_emoji_policy(cls, value):
        return value or "forbidden"

    @field_validator("max_first_message_length", mode="before")
    @classmethod
    def default_max_first_message_length(cls, value):
        return value or 200

    @field_validator("business_details", mode="before")
    @classmethod
    def default_business_details(cls, value):
        return value if isinstance(value, dict) else {}

    @field_validator("owner_clarification_enabled", mode="before")
    @classmethod
    def default_owner_clarification_enabled(cls, value):
        return value is not False


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
    business_details: Optional[dict[str, Any]] = None
    owner_clarification_enabled: Optional[bool] = None


class ScriptResponse(ScriptBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
