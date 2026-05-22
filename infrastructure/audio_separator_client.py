"""
Audio Separator Client — HTTP client to the audio-separator service.

Implements IVoiceSeparator by calling the audio-separator HTTP API
running in Docker container (port 8300).
"""

import base64
import logging
from pathlib import Path

import httpx

from app.domain.interfaces import IVoiceSeparator

logger = logging.getLogger(__name__)


class AudioSeparatorClient(IVoiceSeparator):
    """
    Sends audio to the audio-separator HTTP service and receives clean vocals.

    The service uses UVR models (MDX23C) to extract vocals from mixed audio.
    """

    def __init__(self, separator_url: str = "http://localhost:8300", timeout: float = 300.0) -> None:
        self._separator_url = separator_url.rstrip("/")
        self._timeout = timeout

    async def separate_vocals(self, audio_path: Path, output_path: Path) -> Path:
        """
        Send audio to separator service, receive clean vocals.

        Args:
            audio_path: Path to mixed audio (voice + music/noise).
            output_path: Where to save the isolated vocals.

        Returns:
            Path to the clean vocals file.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Separating vocals: %s → %s (via %s)",
            audio_path.name,
            output_path.name,
            self._separator_url,
        )

        # Read audio and encode as base64
        audio_bytes = audio_path.read_bytes()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._separator_url}/separate_json",
                json={
                    "audio_base64": audio_base64,
                    "filename": audio_path.name,
                },
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"Audio separator error: {response.status_code} - {response.text}"
                )

            result = response.json()
            vocals_base64 = result["vocals_base64"]
            vocals_bytes = base64.b64decode(vocals_base64)

            output_path.write_bytes(vocals_bytes)

        logger.info("Vocals separated: %s (%d bytes)", output_path, len(vocals_bytes))
        return output_path

    async def health_check(self) -> bool:
        """Check if audio-separator service is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._separator_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning("Audio separator health check failed: %s", e)
            return False
