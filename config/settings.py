from functools import lru_cache

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


@lru_cache
def get_settings() -> Settings:
    return Settings()
