"""Direct OmniVoice TTS and voice-cloning adapter.

OmniVoice is loaded lazily from the shared Hugging Face cache, following the
same pattern as HybridVoice. Generation runs in a worker thread so FastAPI's
event loop remains responsive.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from threading import Lock

from app.domain.entities import VoiceDesignParams
from app.domain.interfaces import ITTSSynthesizer
from infrastructure.model_runtime import cached_snapshot, resolve_device

logger = logging.getLogger(__name__)


class OmniVoiceTTSSynthesizer(ITTSSynthesizer):
    """Local OmniVoice Voice Design and Voice Clone implementation."""

    VOICE_INSTRUCTS = {
        "ru": "male", "en": "male", "tr": "male", "az": "male",
        "uk": "male", "es": "male", "fr": "male", "de": "male",
        "it": "male", "pt": "male", "zh": "male", "ja": "male",
        "ko": "male", "ar": "male", "hi": "male",
    }

    def __init__(
        self,
        model_name: str = "k2-fsa/OmniVoice",
        default_voice: str = "female",
        cache_dir: str | Path | None = None,
        device: str = "auto",
        hf_token: str | None = None,
    ) -> None:
        self._model_name = model_name
        self._default_voice = default_voice
        self._cache_dir = cache_dir
        self._requested_device = device
        self._hf_token = hf_token
        self._model = None
        self._model_lock = Lock()
        self._generation_lock = Lock()
        self._device = "unknown"
        self._sampling_rate = 24000

    def _load_model(self):
        if self._model is not None:
            return self._model

        with self._model_lock:
            if self._model is not None:
                return self._model

            import torch
            from omnivoice.models.omnivoice import OmniVoice

            model_path = cached_snapshot(
                self._model_name,
                cache_dir=self._cache_dir,
                token=self._hf_token,
            )
            self._device = resolve_device(self._requested_device)
            dtype = torch.float16 if self._device == "cuda" else torch.float32
            logger.info(
                "Loading OmniVoice from cache: %s (device=%s, dtype=%s)",
                model_path,
                self._device,
                dtype,
            )
            try:
                self._model = OmniVoice.from_pretrained(
                    str(model_path), device_map=self._device, dtype=dtype
                )
            except RuntimeError:
                if self._requested_device not in {None, "", "auto"} or self._device != "cuda":
                    raise
                logger.warning("OmniVoice CUDA initialization failed; retrying on CPU")
                self._device = "cpu"
                self._model = OmniVoice.from_pretrained(
                    str(model_path), device_map="cpu", dtype=torch.float32
                )
            self._sampling_rate = getattr(self._model, "sampling_rate", 24000)
            return self._model

    def _generate_sync(self, **kwargs):
        model = self._load_model()
        with self._generation_lock:
            audio = model.generate(**kwargs)
        return audio[0] if isinstance(audio, list) else audio

    async def _generate(self, **kwargs):
        return await asyncio.to_thread(self._generate_sync, **kwargs)

    async def _save_generated(self, output_path: Path, **kwargs) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        audio = await self._generate(**kwargs)
        import soundfile as sf
        sf.write(str(output_path), audio, self._sampling_rate, format="WAV")
        logger.info("OmniVoice audio saved: %s", output_path)
        return output_path

    def _get_voice_instruct(self, language: str | None) -> str:
        return self.VOICE_INSTRUCTS.get(language or "", self._default_voice)

    async def synthesize(
        self,
        text: str,
        reference_audio_path: Path,
        reference_text: str,
        target_language: str,
        output_path: Path,
    ) -> Path:
        return await self._save_generated(
            output_path,
            text=text,
            language=target_language,
            instruct=self._get_voice_instruct(target_language),
        )

    async def synthesize_with_instruct(
        self, text: str, instruct: str, output_path: Path, language: str | None = None
    ) -> Path:
        return await self._save_generated(
            output_path, text=text, language=language, instruct=instruct
        )

    async def synthesize_with_params(
        self,
        text: str,
        voice_params: VoiceDesignParams,
        target_language: str,
        output_path: Path,
    ) -> Path:
        return await self.synthesize_with_instruct(
            text,
            voice_params.to_instruct_string(),
            output_path,
            target_language,
        )

    async def synthesize_with_clone(
        self,
        text: str,
        ref_audio_path: Path,
        ref_text: str,
        output_path: Path,
        language: str | None = None,
    ) -> Path:
        # Не передаём None: официальный OmniVoice тогда сам загрузит
        # дополнительную ASR-модель для расшифровки reference-аудио.
        # Пустая строка сохраняет клонирование по аудио и не запускает ASR.
        return await self._save_generated(
            output_path,
            text=text,
            language=language,
            ref_audio=str(ref_audio_path),
            ref_text=ref_text or "",
        )

    async def health_check(self) -> bool:
        """Return whether the direct model has been loaded successfully."""
        try:
            self._load_model()
            return True
        except Exception as exc:
            logger.warning("OmniVoice health check failed: %s", exc)
            return False

    @property
    def runtime(self) -> dict[str, str]:
        return {
            "model": self._model_name,
            "device": self._device,
            "sampling_rate": str(self._sampling_rate),
            "loaded": str(self._model is not None).lower(),
        }
