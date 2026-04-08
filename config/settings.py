from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "guest"
    rabbitmq_password: str = "guest"
    rabbitmq_vhost: str = "/"
    exchange_name: str = Field(
        default="rag.events",
        validation_alias=AliasChoices("EXCHANGE_NAME", "exchange_name"),
    )
    rabbitmq_queue_name: str = Field(
        default="rag.tasks",
        validation_alias=AliasChoices("RABBITMQ_QUEUE_NAME", "rabbitmq_queue_name"),
    )
    upload_dir: Path = Field(
        default=Path("data/uploads"),
        validation_alias=AliasChoices("UPLOAD_DIR", "upload_dir"),
    )
    max_upload_bytes: int = Field(
        default=20 * 1024 * 1024,
        validation_alias=AliasChoices("MAX_UPLOAD_BYTES", "max_upload_bytes"),
    )
    qdrant_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("QDRANT_HOST", "qdrant_host"),
    )
    qdrant_port: int = Field(
        default=6333,
        validation_alias=AliasChoices("QDRANT_PORT", "qdrant_port"),
    )
    qdrant_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("QDRANT_API_KEY", "qdrant_api_key"),
    )
    qdrant_https: bool = Field(
        default=False,
        validation_alias=AliasChoices("QDRANT_HTTPS", "qdrant_https"),
    )
    qdrant_prefer_grpc: bool = Field(
        default=False,
        validation_alias=AliasChoices("QDRANT_PREFER_GRPC", "qdrant_prefer_grpc"),
    )
    llm_base_url: str = Field(
        default="http://127.0.0.1:11434/v1",
        validation_alias=AliasChoices("LLM_BASE_URL", "llm_base_url", "LLM_URL"),
    )
    llm_model: str = Field(
        default="phi3:mini",
        validation_alias=AliasChoices("LLM_MODEL", "llm_model"),
    )
    llm_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LLM_API_KEY", "llm_api_key"),
    )
    llm_timeout_seconds: float = Field(
        default=300.0,
        validation_alias=AliasChoices("LLM_TIMEOUT_SECONDS", "llm_timeout_seconds"),
    )
    max_rag_context_chars: int = Field(
        default=12000,
        validation_alias=AliasChoices("MAX_RAG_CONTEXT_CHARS", "max_rag_context_chars"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
