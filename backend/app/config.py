from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "AI News Dashboard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/ainews"

    # API Keys
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # Broadcast
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "ai-news@example.com"

    LINKEDIN_ACCESS_TOKEN: str = ""
    WHATSAPP_API_KEY: str = ""
    WHATSAPP_PHONE_ID: str = ""

    # Scheduler
    FETCH_INTERVAL_MINUTES: int = 15
    MAX_NEWS_AGE_DAYS: int = 7

    # Dedup
    DEDUP_SIMILARITY_THRESHOLD: float = 0.85

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()