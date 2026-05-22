"""
Whisper Transcriber — HTTP client to the local faster-whisper service.

Implements ITranscriber by calling the OpenAI-compatible /v1/audio/transcriptions
endpoint exposed by the faster-whisper-server Docker container.
"""

import logging
from pathlib import Path

import httpx

from app.domain.entities import TranscriptionResult, TranscriptionSegment
from app.domain.interfaces import ITranscriber

logger = logging.getLogger(__name__)


class WhisperTranscriber(ITranscriber):
    """
    Sends audio to the local faster-whisper HTTP service and parses the response.

    The service must expose an OpenAI-compatible transcription endpoint.
    """

    def __init__(self, whisper_url: str, timeout: float = 300.0) -> None:
        self._whisper_url = whisper_url
        self._timeout = timeout

    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """Send audio file to Whisper service, return structured transcription."""

        logger.info("Sending %s to Whisper at %s", audio_path.name, self._whisper_url)

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            with open(audio_path, "rb") as audio_file:
                files = {"file": (audio_path.name, audio_file, "audio/wav")}
                data = {
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": "segment",
                }

                response = await client.post(
                    self._whisper_url,
                    files=files,
                    data=data,
                )
                response.raise_for_status()

        result = response.json()

        # Parse segments from the verbose JSON response
        segments = [
            TranscriptionSegment(
                start=seg.get("start", 0.0),
                end=seg.get("end", 0.0),
                text=seg.get("text", "").strip(),
            )
            for seg in result.get("segments", [])
        ]

        full_text = result.get("text", "").strip()
        if not full_text and segments:
            full_text = " ".join(seg.text for seg in segments)

        detected_language = result.get("language", "unknown")

        logger.info(
            "Whisper transcription complete — language=%s, segments=%d",
            detected_language,
            len(segments),
        )

        return TranscriptionResult(
            segments=segments,
            language=detected_language,
            full_text=full_text,
        )
