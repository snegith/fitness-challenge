"""
Application configuration.

All settings are loaded from environment variables or a .env file via
pydantic-settings.  No scattered os.getenv() calls anywhere in the codebase —
import `settings` from this module instead.

Required environment variables (see .env.example):
    DB_PATH      – filesystem path to the SQLite database file
    JWT_SECRET   – secret key used to sign HS256 tokens (optional feature)
    JWT_EXPIRE_HOURS – token lifetime in hours (default: 24)
    TIMEZONE     – canonical business timezone (must remain "Asia/Kolkata")
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    db_path: str = "fitness.db"

    # JWT  (optional auth feature — HS256)
    jwt_secret: str = "change-me-before-use"
    jwt_expire_hours: int = 24

    # Timezone — fixed by SRS §2.3; do not override in production
    timezone: str = "Asia/Kolkata"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Single shared instance — import this everywhere
settings = Settings()
