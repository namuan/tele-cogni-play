from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""

    # Telegram Configuration
    telegram_bot_token: str
    telegram_user_id: int

    # OpenRouter Configuration
    openrouter_api_key: str
    openrouter_primary_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_fallback_model: str = "anthropic/claude-3-haiku"

    # Database Configuration
    database_path: str = "./data/cogniplay.db"

    # Application Configuration
    log_level: str = "INFO"
    session_timeout_minutes: int = 30
    max_response_time_seconds: int = 3

    # Feature Flags
    enable_analytics: bool = True
    enable_difficulty_adjustment: bool = True
    difficulty_adjustment_threshold: int = 3

    # Backup Configuration
    backup_enabled: bool = True
    backup_interval_hours: int = 24

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
