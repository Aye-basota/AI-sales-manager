from pydantic_settings import BaseSettings
from functools import lru_cache


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

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
