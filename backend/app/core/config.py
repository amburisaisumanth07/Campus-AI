import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str
    CORS_ORIGINS: str = "http://localhost:5173"

    # Authentication
    AUTH_SECRET_KEY: str = "CHANGE-ME-IN-PRODUCTION-USE-A-STRONG-RANDOM-KEY"
    AUTH_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Admin seed (for local dev only)
    ADMIN_EMAIL: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Admin"

    # Document storage
    DOCUMENT_STORAGE_PATH: str = "data/documents"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_MIME_TYPES: str = "application/pdf"

    # Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.1-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    GEMINI_TEMPERATURE: float = 0.0
    GEMINI_MAX_OUTPUT_TOKENS: int = 2048

    # ChromaDB (HttpClient service)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_COLLECTION: str = "campus_docs"

    # RAG tuning
    RAG_CHUNK_SIZE: int = 1000
    RAG_CHUNK_OVERLAP: int = 200
    RAG_TOP_K: int = 4
    RAG_RELEVANCE_THRESHOLD: float = 0.0

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

settings = Settings()
