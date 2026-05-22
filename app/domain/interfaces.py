"""
Domain interfaces — abstract contracts that infrastructure must implement.
Business logic depends ONLY on these interfaces, never on concrete implementations.
"""

from abc import ABC, abstractmethod
from pathlib import Path

from app.domain.entities import TranscriptionResult, TranslationResult, VoiceDesignParams


class ITranscriber(ABC):
    """Contract for Speech-to-Text services."""

    @abstractmethod
    async def transcribe(self, audio_path: Path) -> TranscriptionResult:
        """
        Transcribe an audio file into text segments.

        Args:
            audio_path: Path to the audio file (WAV/MP3).

        Returns:
            TranscriptionResult with detected language and timed segments.
        """
        ...


class ITranslator(ABC):
    """Contract for text translation services."""

    @abstractmethod
    async def translate(self, text: str, source_language: str, target_language: str) -> TranslationResult:
        """
        Translate text from source to target language.

        Args:
            text: Source text to translate.
            source_language: ISO language code of the source (e.g. "en").
            target_language: ISO language code of the target (e.g. "ru").

        Returns:
            TranslationResult with original and translated text.
        """
        ...


class ITTSSynthesizer(ABC):
    """Contract for Text-to-Speech with voice cloning."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        reference_audio_path: Path,
        reference_text: str,
        target_language: str,
        output_path: Path,
    ) -> Path:
        """
        Synthesize speech from text, cloning the voice from a reference audio.

        Args:
            text: Text to speak.
            reference_audio_path: Audio sample for voice cloning.
            reference_text: Transcription of the reference audio.
            target_language: Language of the output speech.
            output_path: Where to save the synthesized audio.

        Returns:
            Path to the generated audio file.
        """
        ...

    @abstractmethod
    async def synthesize_with_clone(
        self,
        text: str,
        ref_audio_path: Path,
        ref_text: str,
        output_path: Path,
        language: str = None,
    ) -> Path:
        """
        Synthesize speech with VOICE CLONING from reference audio.

        The generated voice will match the reference audio speaker.

        Args:
            text: Text to synthesize (translated text).
            ref_audio_path: Path to reference audio for voice cloning.
            ref_text: Transcription of the reference audio.
            output_path: Where to save the synthesized audio.
            language: Target language for correct pronunciation.

        Returns:
            Path to the generated audio file.
        """
        ...

    @abstractmethod
    async def synthesize_with_params(
        self,
        text: str,
        voice_params: VoiceDesignParams,
        target_language: str,
        output_path: Path,
    ) -> Path:
        """
        Synthesize speech using Voice Design with explicit parameters.

        Args:
            text: Text to speak.
            voice_params: Voice attributes (gender, age, pitch, accent, etc.).
            target_language: Language of the output speech.
            output_path: Where to save the synthesized audio.

        Returns:
            Path to the generated audio file.
        """
        ...


class IVoiceSeparator(ABC):
    """Contract for voice/music separation services."""

    @abstractmethod
    async def separate_vocals(self, audio_path: Path, output_path: Path) -> Path:
        """
        Extract clean vocals from mixed audio (remove music/noise).

        Args:
            audio_path: Path to the mixed audio file.
            output_path: Where to save the isolated vocals.

        Returns:
            Path to the clean vocals audio file.
        """
        ...


class IAudioMixer(ABC):
    """Contract for audio extraction and video/audio merging (FFmpeg)."""

    @abstractmethod
    async def extract_audio(self, video_path: Path, output_audio_path: Path) -> Path:
        ...

    @abstractmethod
    async def create_mute_video(self, video_path: Path, output_video_path: Path) -> Path:
        ...

    @abstractmethod
    async def merge_audio_into_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_video_path: Path,
    ) -> Path:
        """
        Replace/overlay the audio track of a video file.

        Args:
            video_path: Path to the original video.
            audio_path: Path to the new audio track.
            output_video_path: Where to save the output video.

        Returns:
            Path to the final video file.
        """
        ...
