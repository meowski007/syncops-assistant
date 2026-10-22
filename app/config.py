import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
RUNBOOKS_DIR = BASE_DIR / "runbooks"
DATA_DIR = BASE_DIR / "data"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # Database
    DATABASE_PATH: str = str(DATA_DIR / "syncops.db")
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_URL: str = "http://localhost:8000"
    
    # Dashboard
    DASHBOARD_PORT: int = 8501
    
    # Alerting & Thresholds
    FAILURE_RATE_THRESHOLD: float = 0.05
    ALERT_COOLDOWN_MINUTES: int = 15
    
    # LLM Optional Config
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str | None = None
    
    # Slack Optional Config
    SLACK_BOT_TOKEN: str | None = None
    SLACK_APP_TOKEN: str | None = None
    SLACK_SIGNING_SECRET: str | None = None
    SLACK_ALERT_CHANNEL: str = "#syncops-alerts"

settings = Settings()
