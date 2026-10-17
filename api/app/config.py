"""Application configuration loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"

    # Nominatim (external geocoding fallback)
    enable_nominatim: bool = True
    nominatim_base_url: str = "https://nominatim.openstreetmap.org"
    nominatim_user_agent: str = "SafePulse/0.1"
    nominatim_contact_email: str = "you@example.com"
    nominatim_min_interval_seconds: float = 1.0

    # Database
    database_url: str = "sqlite:///./safepulse.db"

    # CORS
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def gemini_configured(self) -> bool:
        return bool(self.gemini_api_key.strip())

    @property
    def user_agent(self) -> str:
        return f"{self.nominatim_user_agent} (contact: {self.nominatim_contact_email})"


@lru_cache
def get_settings() -> Settings:
    return Settings()
