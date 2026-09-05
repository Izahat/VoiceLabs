"""Application service for the currently supported OmniVoice workflows.

Video dubbing and machine translation are intentionally not part of this
service. They are planned features and must not be initialized on startup.
"""

import logging
import shutil
import uuid
from pathlib import Path

from app.domain.interfaces import ITranscriber, ITTSSynthesizer, IVoiceSeparator
from app.domain.entities import VoiceDesignParams

logger = logging.getLogger(__name__)


class VoiceService:
    """Coordinate voice cloning and text-to-speech with OmniVoice."""

    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

    def __init__(
        self,
        transcriber: ITranscriber,
        tts_synthesizer: ITTSSynthesizer,
        voice_separator: IVoiceSeparator | None,
        use_voice_separation: bool,
        temp_dir: Path,
        output_dir: Path,
    ) -> None:
        self._transcriber = transcriber
        self._tts = tts_synthesizer
        self._voice_separator = voice_separator
        self._use_voice_separation = use_voice_separation
        self._temp_dir = temp_dir
        self._output_dir = output_dir

    async def clone_voice(self, ref_audio_path: Path) -> str:
        """Create a reusable OmniVoice profile from an audio/video reference."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
        voice_id = uuid.uuid4().hex[:12]
        voice_dir = self._output_dir / f"voice_{voice_id}"
        voice_dir.mkdir(parents=True, exist_ok=True)

        clean_audio_path = ref_audio_path
        if self._use_voice_separation and self._voice_separator is not None:
            try:
                health_check = getattr(self._voice_separator, "health_check", None)
                if health_check is not None and not await health_check():
                    logger.warning("Audio Separator is unavailable; using original reference")
                else:
                    clean_audio_path = await self._voice_separator.separate_vocals(
                        audio_path=ref_audio_path,
                        output_path=voice_dir / "clean_vocals.wav",
                    )
            except Exception as exc:
                logger.warning("Voice separation failed; using original reference: %s", exc)

        stored_ref = voice_dir / "reference.wav"
        shutil.copy2(clean_audio_path, stored_ref)

        # Создание профиля не должно запускать общий Faster Whisper.
        # Whisper относится к отдельному сценарию транскрипции. OmniVoice
        # получает аудиоссылку без текста-образца; пустая строка намеренно
        # отключает его необязательную автоматическую ASR-транскрипцию.
        ref_text = ""
        (voice_dir / "ref_text.txt").write_text(ref_text, encoding="utf-8")
        logger.info(
            "Voice profile prepared without ASR reference transcription: %s",
            voice_id,
        )
        logger.info("Voice cloned: %s -> %s", ref_audio_path.name, voice_id)
        return voice_id

    async def synthesize_with_voice_id(
        self, text: str, voice_id: str, language: str | None = None
    ) -> Path:
        """Synthesize text using an existing cloned voice profile."""
        voice_dir = self._output_dir / f"voice_{voice_id}"
        if not voice_dir.exists():
            raise ValueError(f"Voice not found: {voice_id}")

        ref_audio_path = voice_dir / "reference.wav"
        ref_text_path = voice_dir / "ref_text.txt"
        ref_text = ref_text_path.read_text(encoding="utf-8") if ref_text_path.exists() else ""
        output_path = self._output_dir / f"tts_{voice_id}.wav"

        return await self._tts.synthesize_with_clone(
            text=text,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            output_path=output_path,
            language=language,
        )

    async def synthesize_with_voice_design(
        self,
        text: str,
        voice_params: VoiceDesignParams,
        language: str,
        output_path: Path,
    ) -> Path:
        """Synthesize speech using OmniVoice voice-design parameters."""
        return await self._tts.synthesize_with_params(
            text=text,
            voice_params=voice_params,
            target_language=language,
            output_path=output_path,
        )

    @property
    def runtime(self) -> dict:
        """Expose model/device state without forcing a model download."""
        return {
            "asr": getattr(self._transcriber, "runtime", {}),
            "tts": getattr(self._tts, "runtime", {}),
        }

    @property
    def transcriber(self) -> ITranscriber:
        """Return the shared ASR adapter used by the transcription workflow."""
        return self._transcriber
