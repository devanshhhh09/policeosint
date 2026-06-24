from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import List, Optional
import secrets

class Settings(BaseSettings):
    APP_NAME: str = "PoliceOSINT"
    APP_ENV: str = "development"
    DEBUG: bool = False
    SECRET_KEY: str = secrets.token_hex(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    DATABASE_URL: str = "postgresql+asyncpg://policeosint:policeosint_secret@localhost:5432/policeosint"
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    SHODAN_API_KEY: Optional[str] = None
    VIRUSTOTAL_API_KEY: Optional[str] = None
    HUNTER_IO_API_KEY: Optional[str] = None
    IPINFO_TOKEN: Optional[str] = None
    HIBP_API_KEY: Optional[str] = None
    OTX_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    TELEGRAM_API_ID:   Optional[str] = None
    TELEGRAM_API_HASH: Optional[str] = None
    TELEGRAM_PHONE:    Optional[str] = None
    TELEGRAM_AUTO_CHANNELS: str = ""  # comma-separated channel usernames
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    EVIDENCE_UPLOAD_DIR: str = "/app/evidence"
    MAX_UPLOAD_SIZE_MB: int = 100

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}

settings = Settings()
