from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sales:salespass@localhost:5432/ai_sales"
    redis_url: str = "redis://localhost:6379/0"

    # LLM provider selection: "dashscope" or "openrouter"
    llm_provider: str = "dashscope"

    # OpenRouter settings
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # DashScope (Alibaba Cloud) settings
    dashscope_api_key: str = ""
    dashscope_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"

    admin_bot_token: str = ""
    admin_notification_chat_id: str = ""
    secret_key: str = "changeme"
    session_encryption_key: str = ""
    telegram_api_id: int = 0
    telegram_api_hash: str = ""
    daily_message_limit: int = 50
    debug: bool = True

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        if normalized in {"release", "prod", "production", "off", "false", "0", "no"}:
            return False
        if normalized in {"debug", "dev", "development", "on", "true", "1", "yes"}:
            return True
        return value

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
