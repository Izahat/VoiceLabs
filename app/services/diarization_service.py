"""
Speaker Diarization Service — calls Sherpa-onnx Docker container.

Provides speaker segmentation and clustering for audio files.
Uses HTTP client to communicate with the Sherpa Docker service.
"""

import asyncio
import logging
from pathlib import Path
from typing import List

from config.settings import get_settings

logger = logging.getLogger(__name__)


class DiarizationService:
    """Speaker diarization via Sherpa-onnx HTTP service."""

    def __init__(self):
        self._settings = get_settings()
        self._client = None

    def _get_client(self):
        """Lazy load the HTTP client based on provider setting."""
        if self._client is None:
            provider = self._settings.diarization_provider
            if provider == "pyannote":
                from infrastructure.pyannote_diarization_client import PyAnnoteDiarizationClient
                self._client = PyAnnoteDiarizationClient(
                    base_url=self._settings.pyannote_diarization_url
                )
            else:
                from infrastructure.sherpa_diarization_client import SherpaDiarizationClient
                self._client = SherpaDiarizationClient(
                    base_url=self._settings.sherpa_diarization_url
                )
        return self._client

    async def identify_speakers(self, audio_path: Path) -> List[dict]:
        """
        Identify speakers in an audio file using Sherpa-onnx service.

        Args:
            audio_path: Path to the audio file

        Returns:
            List of speaker segments with:
                - speaker: speaker ID (SPEAKER_00, SPEAKER_01, etc.)
                - start: start time in seconds
                - end: end time in seconds
                - confidence: confidence score
        """
        try:
            client = self._get_client()

            # Check if service is available
            if not await client.health_check():
                logger.warning("Sherpa diarization service not available, using fallback")
                return await self._fallback_diarization(audio_path)

            # Call the Sherpa service
            result = await client.diarize(audio_path)

            # Convert to our format
            segments = result.get("segments", [])
            return [
                {
                    "speaker": seg.get("speaker", "SPEAKER_00"),
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", 0.0),
                    "confidence": seg.get("confidence", 0.8),
                }
                for seg in segments
            ]

        except Exception as e:
            logger.warning("Sherpa diarization failed: %s", e)
            return await self._fallback_diarization(audio_path)

    async def _fallback_diarization(self, audio_path: Path) -> List[dict]:
        """
        Simple fallback diarization when Sherpa service is unavailable.
        Returns one speaker for the entire audio.
        """
        duration = await self._get_duration(audio_path)
        if duration <= 0:
            duration = 30.0

        return [{
            "speaker": "SPEAKER_00",
            "start": 0.0,
            "end": duration,
            "confidence": 0.5,
        }]

    async def _get_duration(self, audio_path: Path) -> float:
        """Get audio file duration using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return float(stdout.decode().strip())
        except Exception:
            pass
        return 0.0

    async def count_speakers(self, audio_path: Path) -> int:
        """Count unique speakers."""
        speakers = await self.identify_speakers(audio_path)
        unique = set(s["speaker"] for s in speakers)
        return len(unique)

    def get_speaker_colors(self, num_speakers: int) -> List[str]:
        """Get colors for speakers (for UI)."""
        colors = [
            "#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4",
            "#FFEAA7", "#DDA0DD", "#98D8C8", "#F7DC6F",
            "#BB8FCE", "#85C1E9"
        ]
        return [colors[i % len(colors)] for i in range(num_speakers)]