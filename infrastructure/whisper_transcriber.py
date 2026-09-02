"""Direct faster-whisper Turbo ASR adapter.

The model is loaded lazily from the shared Hugging Face cache. No HTTP or
Docker service is involved in transcription.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from threading import Lock

from app.domain.entities import TranscriptionResult, TranscriptionSegment
from app.domain.interfaces import ITranscriber
from infrastructure.model_runtime import cached_snapshot, resolve_whisper_runtime

logger = logging.getLogger(__name__)


class WhisperTranscriber(ITranscriber):
    """Transcribe audio with `deepdml/faster-whisper-large-v3-turbo-ct2`."""

    def __init__(
        self,
        model_name: str = "deepdml/faster-whisper-large-v3-turbo-ct2",
        cache_dir: str | Path | None = None,
        device: str = "auto",
        compute_type: str = "auto",
        hf_token: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._requested_device = device
        self._requested_compute_type = compute_type
        self._hf_token = hf_token
        self._model = None
        self._model_lock = Lock()
        self._device = "unknown"
        self._compute_type = "unknown"

    def _load_model(self):
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model

            from faster_whisper import WhisperModel

            model_path = cached_snapshot(
                self._model_name,
                cache_dir=self._cache_dir,
                token=self._hf_token,
            )
            self._device, self._compute_type = resolve_whisper_runtime(
                self._requested_device,
                self._requested_compute_type,
            )
            logger.info(
                "Loading Whisper Turbo from cache: %s (device=%s, compute_type=%s)",
                model_path,
                self._device,
                self._compute_type,
            )
            try:
                self._model = WhisperModel(
                    str(model_path),
                    device=self._device,
                    compute_type=self._compute_type,
                )
            except RuntimeError:
                if self._requested_device not in {None, "", "auto"} or self._device != "cuda":
                    raise
                logger.warning("Whisper CUDA initialization failed; retrying on CPU int8")
                self._device, self._compute_type = "cpu", "int8"
                self._model = WhisperModel(
                    str(model_path), device="cpu", compute_type="int8"
                )
            return self._model

    def _transcribe_sync(self, audio_path: Path, language: str | None) -> TranscriptionResult:
        model = self._load_model()
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=None if not language or language == "auto" else language,
            beam_size=5,
            temperature=0.0,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        segments = [
            TranscriptionSegment(
                start=segment.start,
                end=segment.end,
                text=segment.text.strip(),
            )
            for segment in segments_iter
        ]
        full_text = " ".join(segment.text for segment in segments).strip()
        logger.info(
            "Whisper Turbo transcription complete — language=%s, segments=%d, device=%s",
            info.language,
            len(segments),
            self._device,
        )
        return TranscriptionResult(
            segments=segments,
            language=info.language or "unknown",
            full_text=full_text,
        )

    async def transcribe(
        self, audio_path: Path, language: str | None = None
    ) -> TranscriptionResult:
        """Run blocking model inference off the FastAPI event loop."""
        return await asyncio.to_thread(self._transcribe_sync, audio_path, language)

    @property
    def runtime(self) -> dict[str, str]:
        return {
            "model": self._model_name,
            "device": self._device,
            "compute_type": self._compute_type,
            "loaded": str(self._model is not None).lower(),
        }
