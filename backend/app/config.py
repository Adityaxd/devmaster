"""
DevMaster API Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "DevMaster"
    app_version: str = "0.1.0"
    debug: bool = True
    
    # API
    api_v1_str: str = "/api/v1"
    
    # Database
    database_url: str = "postgresql://devmaster:devmaster@localhost:5433/devmaster"
    async_database_url: str = "postgresql+asyncpg://devmaster:devmaster@localhost:5433/devmaster"
    
    # Security
    secret_key: str = "your-secret-key-here-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # CORS
    backend_cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Redis (for Celery)
    redis_url: str = "redis://redis:6379/0"
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()