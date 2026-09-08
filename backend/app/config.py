"""
LADRIS — Application Configuration
Loads all settings from environment variables / .env file.
"""
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict



class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ─────────────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_NAME: str = "LADRIS"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # ─── Database ─────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ladris"
    POSTGRES_USER: str = "ladris_user"
    POSTGRES_PASSWORD: str

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def SYNC_DATABASE_URL(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # ─── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Security ─────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    BCRYPT_ROUNDS: int = 12

    @property
    def cors_origins(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    # ─── Server ───────────────────────────────────────────────────────────────
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # ─── Data.gov.in Integration ──────────────────────────────────────────────
    DATAGOV_API_KEY: str = ""
    # Get free API key at: https://data.gov.in (click Register → My Account → Generate API Key)

    # ─── BhoomiRashi Scraper Settings ────────────────────────────────────────
    BHOOMIRASHI_SCRAPE_DELAY_SECONDS: float = 2.0   # polite crawl delay
    BHOOMIRASHI_MAX_PROJECTS_PER_STATE: int = 500   # cap per state
    BHOOMIRASHI_TIMEOUT_SECONDS: float = 30.0

    # ─── ETL Settings ─────────────────────────────────────────────────────────
    ETL_BATCH_SIZE: int = 50                        # DB upsert batch size
    ETL_DATA_DIR: str = "data"                      # relative to backend/

    # ─── First Admin Seed ─────────────────────────────────────────────────────
    FIRST_ADMIN_EMAIL: str = "admin@ladris.gov.in"
    FIRST_ADMIN_PASSWORD: str = ""
    FIRST_ADMIN_NAME: str = "System Administrator"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
