from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sales:salespass@localhost:5432/ai_sales"
    redis_url: str = "redis://localhost:6379/0"
    openrouter_api_key: str = ""
    admin_bot_token: str = ""
    secret_key: str = "changeme"
    debug: bool = True

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
