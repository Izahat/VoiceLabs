"""
Centralized application settings.
All values are loaded from .env — zero hardcoding.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Immutable application configuration sourced from environment variables."""

    # --- General ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    temp_dir: Path = Path("./tmp")
    output_dir: Path = Path("./output")

    # --- Whisper Service ---
    whisper_base_url: str = "http://localhost:8100"
    whisper_endpoint: str = "/v1/audio/transcriptions"

    # --- Translation Model ---
    translation_provider: str = "gemini"
    gemini_api_key: str = ""
    translation_model: str = "gemini-2.0-flash"

    # --- TTS (OmniVoice — HTTP API, 600+ languages) ---
    omnivoice_url: str = "http://localhost:8200"
    omnivoice_voice: str = "english_male"

    # --- Voice Separator (audio-separator, UVR models) ---
    audio_separator_url: str = "http://localhost:8300"
    use_voice_separation: bool = False  # Enable for better voice cloning quality

    # --- FFmpeg ---
    ffmpeg_path: str = "ffmpeg"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @property
    def whisper_url(self) -> str:
        """Full URL for the Whisper transcription endpoint."""
        return f"{self.whisper_base_url}{self.whisper_endpoint}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for application settings."""
    return Settings()
