import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "Oasis B2B Restaurant Reservation & Inventory System"
    APP_VERSION: str = "1.0.0"
    ENV: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./oasis_b2b.db"
    
    # Redis (Fallback to in-memory broadcast if Redis is unavailable)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Server & CORS
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "*"
    ]
    
    # Business Defaults
    DEFAULT_TIMEZONE: str = "Asia/Tashkent"
    DEFAULT_AVG_TURN_TIME_MINS: int = 90
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
