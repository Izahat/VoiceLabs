"""
Sherpa Diarization Client — HTTP client to the Sherpa-onnx diarization service.
"""

import logging
import base64
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


class SherpaDiarizationClient:
    """Client for calling the Sherpa-onnx diarization HTTP service."""

    def __init__(self, base_url: str = "http://localhost:8400", timeout: float = 300.0):
        self._base_url = base_url
        self._timeout = timeout

    async def health_check(self) -> bool:
        """Check if the diarization service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self._base_url}/health")
                return resp.status_code == 200
        except Exception as e:
            logger.warning("Sherpa health check failed: %s", e)
            return False

    async def diarize(self, audio_path: Path) -> dict:
        """
        Perform speaker diarization on an audio file.

        Args:
            audio_path: Path to the audio file

        Returns:
            Dict with speaker segments:
                - status: "ok"
                - num_speakers: number of unique speakers
                - segments: list of {speaker, start, end}
        """
        logger.info("Sending %s to Sherpa diarization at %s", audio_path.name, self._base_url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            with open(audio_path, "rb") as audio_file:
                files = {"file": (audio_path.name, audio_file, "audio/wav")}
                response = await client.post(
                    f"{self._base_url}/diarize",
                    files=files,
                )
                response.raise_for_status()

        result = response.json()
        logger.info(
            "Diarization complete: %d speaker(s), %d segments",
            result.get("num_speakers", 0),
            len(result.get("segments", [])),
        )
        return result

    async def diarize_base64(self, audio_base64: str, filename: str = "audio.wav") -> dict:
        """
        Perform diarization with base64-encoded audio.

        Args:
            audio_base64: Base64-encoded audio data
            filename: Original filename

        Returns:
            Dict with speaker segments
        """
        audio_bytes = base64.b64decode(audio_base64)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            files = {"file": (filename, audio_bytes, "audio/wav")}
            response = await client.post(
                f"{self._base_url}/diarize",
                files=files,
            )
            response.raise_for_status()

        return response.json()