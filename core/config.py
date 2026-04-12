from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from ``.env``."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="allow",
    )

    DATA_DIR: str = "data"
    SESSIONS_DIR: str = "data/sessions"
    VECTOR_DB_DIR: str = "data/vectorstore"
    LOG_DIR: str = "logs"
    MODELS_DIR: str = "models"
    EMBEDDINGS_CACHE_DIR: str = "embeddings_cache"
    EXPORT_DIR: str = "export"
    MEMORY_LOG_DIR: str = "data/memory_log"
    MEMORY_STORE_BACKEND: str = "memory"  # `memory` or `file`

    DEFAULT_STORE_BACKEND: str = "memory"  # ``memory`` or ``file``
    VECTOR_DB_BACKEND: str = "memory"  # ``memory`` or ``chromadb``

    # LLM configuration
    LLM_BACKEND: str = "openai"
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Logging / feedback
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_JSON: bool = False

    # AutoTrainer
    AUTOTRAINER_FREQUENCY_HOURS: int = 24

    # Security / Auth
    AUTH_ENABLED: bool = False
    API_AUTH_ENABLED: bool = False
    RATE_LIMITS_ENABLED: bool = True

settings = Settings()

for path in [
    settings.DATA_DIR,
    settings.SESSIONS_DIR,
    settings.VECTOR_DB_DIR,
    settings.LOG_DIR,
    settings.MEMORY_LOG_DIR,
    settings.MODELS_DIR,
    settings.EMBEDDINGS_CACHE_DIR,
    settings.EXPORT_DIR,
]:
    Path(path).mkdir(parents=True, exist_ok=True)
