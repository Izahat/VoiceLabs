"""
Service Factory — Dependency Injection provider.

Creates and wires all concrete implementations to their interfaces.
This is the ONLY place where concrete classes are instantiated.
If you swap an infrastructure component, you only change THIS file.

"""

from app.domain.interfaces import ITranscriber, ITTSSynthesizer
from app.services.voice_service import VoiceService
from config.settings import Settings
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
            model_name=self._settings.whisper_model_repo,
            cache_dir=self._settings.model_cache_dir,
            device=self._settings.whisper_device,
            compute_type=self._settings.whisper_compute_type,
            hf_token=self._settings.hf_token or None,
        )

    def create_tts_synthesizer(self) -> ITTSSynthesizer:
        """Create the TTS synthesizer using OmniVoice (600+ languages, voice cloning)."""
        return OmniVoiceTTSSynthesizer(
            model_name=self._settings.omnivoice_model,
            default_voice=self._settings.omnivoice_voice,
            cache_dir=self._settings.model_cache_dir,
            device=self._settings.ai_device,
            hf_token=self._settings.hf_token or None,
        )

    def create_voice_service(self) -> VoiceService:
        """Create the active OmniVoice-only application service."""
        return VoiceService(
            transcriber=self.create_transcriber(),
            tts_synthesizer=self.create_tts_synthesizer(),
            voice_separator=None,
            use_voice_separation=False,
            temp_dir=self._settings.temp_dir,
            output_dir=self._settings.output_dir,
        )
