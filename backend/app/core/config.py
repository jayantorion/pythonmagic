import os
from pathlib import Path
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directory for the backend
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
STORAGE_DIR = BASE_DIR / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

# Config directory for external YAML files (in project root, not backend)
PROJECT_ROOT = BASE_DIR.parent
CONFIG_DIR = PROJECT_ROOT / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # General
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = "development-secret-key-change-in-production"
    APP_TITLE: str = "AI Job Search & Application Intelligence Platform"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = f"sqlite+aiosqlite:///{DATA_DIR / 'job_agent.db'}"

    # AI Configuration
    AI_PROVIDER: str = "anthropic"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_FAST_MODEL: str = "claude-3-5-haiku-20241022"

    # Embeddings
    EMBEDDING_PROVIDER: str = "local"  # 'local' or 'openai'
    OPENAI_API_KEY: str = ""

    # Job Feeds
    ADZUNA_APP_ID: str = ""
    ADZUNA_APP_KEY: str = ""
    ADZUNA_COUNTRY: str = "in"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    # Candidate Preferences Config
    CANDIDATE_CONFIG_PATH: Path = CONFIG_DIR / "candidate_preferences.yaml"

    # JWT Authentication
    JWT_SECRET_KEY: str = "change-this-to-a-secure-random-secret-key-for-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
