from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str
    redis_url: str = "redis://localhost:6379/0"
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    cors_origins: str = "http://localhost:5173"
    executor_timeout_seconds: int = 10
    executor_memory_mb: int = 512
    model: str = "claude-sonnet-4-6"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
