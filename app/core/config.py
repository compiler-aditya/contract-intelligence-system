"""Application configuration settings"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Contract Intelligence System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/contract_intelligence"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "contract_intelligence"

    # LLM API Keys (use either OpenAI or Gemini)
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # Model Configuration
    LLM_PROVIDER: str = "gemini"  # "openai" or "gemini"
    OPENAI_MODEL: str = "gpt-4-turbo-preview"
    GEMINI_MODEL: str = "gemini-2.5-flash"  # or "gemini-1-5-flash" or "gemini-pro"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Vector Database
    VECTOR_DB: str = "chromadb"
    CHROMA_PERSIST_DIR: str = "./data/chroma"

    # File Storage
    UPLOAD_DIR: str = "./data/uploads"
    MAX_FILE_SIZE: int = 10485760  # 10MB

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Webhook
    WEBHOOK_TIMEOUT: int = 30
    WEBHOOK_RETRY_COUNT: int = 3

    # Metrics
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Processing
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_WORKERS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables


settings = Settings()
