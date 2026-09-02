"""
Centralized application settings.
All values are loaded from .env — zero hardcoding.
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Immutable application configuration sourced from environment variables."""

    # --- General ---
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    temp_dir: Path = Path("./tmp")
    output_dir: Path = Path("./output")

    # --- Persistence and file storage ---
    database_url: str = "sqlite+aiosqlite:///./data/voicelabs.db"
    storage_dir: Path = Path("./data/storage")

    # --- Direct local model runtime ---
    whisper_model_repo: str = "deepdml/faster-whisper-large-v3-turbo-ct2"
    omnivoice_model: str = "k2-fsa/OmniVoice"
    model_cache_dir: Optional[str] = None
    hf_token: str = ""
    whisper_device: str = "auto"
    whisper_compute_type: str = "auto"
    omnivoice_voice: str = "female"
    ai_device: str = "auto"

    # --- Speaker Diarization (Sherpa-onnx or PyAnnote) ---
    diarization_provider: str = "pyannote"  # "pyannote" or "sherpa"
    sherpa_diarization_url: str = "http://localhost:8400"
    pyannote_diarization_url: str = "http://localhost:8400"

    # --- FFmpeg ---
    ffmpeg_path: str = "ffmpeg"

    # --- Video Downloader (yt-dlp) ---
    video_download_timeout: int = 600  # 10 minutes

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton accessor for application settings."""
    return Settings()
