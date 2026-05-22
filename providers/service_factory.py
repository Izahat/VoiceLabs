"""
Service Factory — Dependency Injection provider.

Creates and wires all concrete implementations to their interfaces.
This is the ONLY place where concrete classes are instantiated.
If you swap an infrastructure component, you only change THIS file.

"""

from app.domain.interfaces import IAudioMixer, ITranscriber, ITranslator, ITTSSynthesizer, IVoiceSeparator
from app.services.dubbing_orchestrator import DubbingOrchestrator
from config.settings import Settings
from infrastructure.audio_separator_client import AudioSeparatorClient
from infrastructure.ffmpeg_audio_mixer import FFmpegAudioMixer
from infrastructure.llm_translator import LLMTranslator
from infrastructure.omnivoice_tts_synthesizer import OmniVoiceTTSSynthesizer
from infrastructure.whisper_transcriber import WhisperTranscriber


class ServiceFactory:
    """
    Composition Root — assembles the full dependency graph.

    Follows the Dependency Inversion Principle:
    - Business logic depends on interfaces (domain layer)
    - This factory resolves interfaces to concrete implementations
    - Changing a provider requires editing only this file
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def create_transcriber(self) -> ITranscriber:
        """Create the speech-to-text transcriber."""
        return WhisperTranscriber(
            whisper_url=self._settings.whisper_url,
        )

    def create_translator(self) -> ITranslator:
        """Create the text translator."""
        return LLMTranslator(
            api_key=self._settings.gemini_api_key,
            model_name=self._settings.translation_model,
        )

    def create_tts_synthesizer(self) -> ITTSSynthesizer:
        """Create the TTS synthesizer using OmniVoice (600+ languages, voice cloning)."""
        return OmniVoiceTTSSynthesizer(
            omnivoice_url=self._settings.omnivoice_url,
            default_voice=self._settings.omnivoice_voice,
        )

    def create_audio_mixer(self) -> IAudioMixer:
        """Create the audio extraction / merging service."""
        return FFmpegAudioMixer(
            ffmpeg_path=self._settings.ffmpeg_path,
        )

    def create_voice_separator(self) -> IVoiceSeparator:
        """Create the voice/music separation service."""
        return AudioSeparatorClient(
            separator_url=self._settings.audio_separator_url,
        )

    def create_orchestrator(self) -> DubbingOrchestrator:
        """
        Create the fully-wired dubbing orchestrator.

        This is the main entry point — all dependencies are resolved here.
        """
        return DubbingOrchestrator(
            transcriber=self.create_transcriber(),
            translator=self.create_translator(),
            tts_synthesizer=self.create_tts_synthesizer(),
            audio_mixer=self.create_audio_mixer(),
            voice_separator=self.create_voice_separator(),
            use_voice_separation=self._settings.use_voice_separation,
            temp_dir=self._settings.temp_dir,
            output_dir=self._settings.output_dir,
        )
