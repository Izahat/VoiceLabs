"""
Transcription Service — high-level service for audio/video transcription.
"""

import logging
from pathlib import Path
from typing import Optional

from app.domain.entities import TranscriptionResult
from app.domain.interfaces import ITranscriber
from infrastructure.whisper_transcriber import WhisperTranscriber
from config.settings import get_settings

logger = logging.getLogger(__name__)


class TranscriptionService:
    """High-level service for transcribing audio/video files."""

    def __init__(self, transcriber: Optional[ITranscriber] = None):
        settings = get_settings()
        self._transcriber = transcriber or WhisperTranscriber(
            model_name=settings.whisper_model_repo,
            cache_dir=settings.model_cache_dir,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            hf_token=settings.hf_token or None,
        )

    async def transcribe(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> dict:
        """
        Transcribe audio file and return structured result.

        Args:
            audio_path: Path to the audio file (WAV, MP3, etc.)
            language: Optional language code hint (auto-detected if None)

        Returns:
            Dict with:
                - language: detected or specified language code
                - text: full transcribed text
                - segments: list of segments with start, end, text
                - duration: audio duration in seconds
        """
        logger.info("Starting transcription: %s", audio_path)

        # Run transcription
        result: TranscriptionResult = await self._transcriber.transcribe(audio_path, language=language)

        # Build response
        response = {
            "language": language or result.language,
            "text": result.full_text,
            "segments": [
                {
                    "start": seg.start,
                    "end": seg.end,
                    "text": seg.text,
                }
                for seg in result.segments
            ],
            "duration": self._get_duration(audio_path),
        }

        logger.info(
            "Transcription complete: %d segments, %d chars",
            len(response["segments"]),
            len(response["text"]),
        )

        return response

    def _get_duration(self, audio_path: Path) -> Optional[float]:
        """Get audio file duration using ffprobe."""
        import subprocess
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        return None

    @property
    def runtime(self) -> dict:
        """Expose ASR model/device state without loading the model."""
        return getattr(self._transcriber, "runtime", {})
