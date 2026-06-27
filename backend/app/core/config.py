from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str = "2024-10-21"

    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    embedding_dimensions: int = 1536

    azure_search_endpoint: str
    azure_search_key: str
    azure_search_index: str = "enterprise-kb-index"

    azure_storage_connection_string: str | None = None
    azure_storage_container: str = "enterprise-kb"

    applicationinsights_connection_string: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()