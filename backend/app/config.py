from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Agentic AI Document Intelligence Platform"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/docintel"

    # Gemini Developer API (Google AI Studio free tier supported).
    gemini_api_key: str = ""
    gemini_chat_model: str = "gemini-3.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 1536

    cors_origins: str = "http://localhost:5173"
    max_upload_mb: int = 15
    confidence_threshold: float = 0.62
    max_retries: int = 1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
