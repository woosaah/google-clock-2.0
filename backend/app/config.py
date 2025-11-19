"""Configuration management using Pydantic settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost/googleclock"
    colehub_database_url: str = ""

    # API Keys
    openweather_api_key: str = ""
    google_calendar_credentials: str = ""

    # Server Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 5000
    ai_server_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"

    # Media Configuration
    media_dir: str = "/media/clock"
    thumbnail_dir: str = "/media/clock/thumbnails"
    max_queue_size: int = 50
    auto_play_queue: bool = True
    enable_transcoding: bool = False
    slideshow_duration: int = 10  # seconds

    # Voice Assistant
    wake_word_enabled: bool = True
    voice_sensitivity: float = 0.5

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    cors_origins: str = "http://localhost:3000"

    # Logging
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
