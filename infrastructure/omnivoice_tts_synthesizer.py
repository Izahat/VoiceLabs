"""
OmniVoice TTS Synthesizer — uses OmniVoice HTTP API server.

Voice Design mode only - describe voice with text attributes.
No reference audio needed.
Supports 600+ languages.
GitHub: https://github.com/k2-fsa/OmniVoice
"""

import logging
from pathlib import Path

import httpx

from app.domain.entities import VoiceDesignParams
from app.domain.interfaces import ITTSSynthesizer

logger = logging.getLogger(__name__)


class OmniVoiceTTSSynthesizer(ITTSSynthesizer):
    """
    Synthesizes speech using OmniVoice HTTP API.
    
    Voice Design mode:
    - No reference audio needed
    - Describe voice with text attributes (gender, age, pitch, style, accent)
    - Supports 600+ languages
    
    Voice attributes:
    - gender: "male" or "female"
    - age: "child", "teenager", "young adult", "middle-aged", "elderly"
    - pitch: "very low pitch", "low pitch", "moderate pitch", "high pitch", "very high pitch"
    - style: "whisper"
    - accent: "american accent", "british accent", "australian accent", etc.
    
    Examples:
    - "male" → simple male voice
    - "female, young adult, high pitch" → young female with high voice
    - "male, elderly, low pitch, whisper" → whispering old man
    - "female, british accent" → British female voice
    """

    # Language code -> voice instruct mapping
    VOICE_INSTRUCTS = {
        # Russian
        "ru": "male",
        "ru_female": "female",
        
        # English
        "en": "male",
        "en_female": "female",
        
        # Turkish
        "tr": "male",
        "tr_female": "female",
        
        # Azerbaijani
        "az": "male",
        "az_female": "female",
        
        # Ukrainian
        "uk": "male",
        "uk_female": "female",
        
        # Spanish
        "es": "male",
        "es_female": "female",
        
        # French
        "fr": "male",
        "fr_female": "female",
        
        # German
        "de": "male",
        "de_female": "female",
        
        # Italian
        "it": "male",
        "it_female": "female",
        
        # Portuguese
        "pt": "male",
        "pt_female": "female",
        
        # Chinese
        "zh": "male",
        "zh_female": "female",
        
        # Japanese
        "ja": "male",
        "ja_female": "female",
        
        # Korean
        "ko": "male",
        "ko_female": "female",
        
        # Arabic
        "ar": "male",
        "ar_female": "female",
        
        # Hindi
        "hi": "male",
        "hi_female": "female",
    }

    def __init__(
        self,
        omnivoice_url: str = "http://localhost:8200",
        default_voice: str = "female",
    ):
        self._omnivoice_url = omnivoice_url.rstrip("/")
        self._default_voice = default_voice

    def _get_voice_instruct(self, language: str) -> str:
        """Get voice instruct string for language code."""
        # Try direct match
        if language in self.VOICE_INSTRUCTS:
            return self.VOICE_INSTRUCTS[language]
        
        # Try with _female suffix
        female_key = f"{language}_female"
        if female_key in self.VOICE_INSTRUCTS:
            return self.VOICE_INSTRUCTS[female_key]
        
        # Fallback to default
        logger.warning(f"Unknown language '{language}', using default voice")
        return self._default_voice

    async def synthesize(
        self,
        text: str,
        reference_audio_path: Path,
        reference_text: str,
        target_language: str,
        output_path: Path,
    ) -> Path:
        """
        Synthesize speech using Voice Design mode.
        
        Note: reference_audio_path and reference_text are ignored in Voice Design mode.
        Voice is created from text description (gender, age, pitch, etc.).
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get voice instruct for language
        voice_instruct = self._get_voice_instruct(target_language)
        
        logger.info(
            "Synthesizing %d chars with OmniVoice Voice Design (language: %s, voice: %s)",
            len(text),
            target_language,
            voice_instruct,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._omnivoice_url}/synthesize",
                json={
                    "text": text,
                    "voice": voice_instruct,
                    "language": target_language,
                },
            )
            
            if response.status_code != 200:
                raise RuntimeError(
                    f"OmniVoice synthesize error: {response.status_code} - {response.text}"
                )
            
            output_path.write_bytes(response.content)

        logger.info("OmniVoice synthesis complete: %s", output_path)
        return output_path

    async def synthesize_with_instruct(
        self,
        text: str,
        instruct: str,
        output_path: Path,
        language: str = None,
    ) -> Path:
        """
        Advanced synthesis with custom voice instruct.
        
        Args:
            text: Text to synthesize
            instruct: Voice description (e.g., "female, young adult, high pitch, british accent")
            output_path: Where to save the audio
            language: Optional language code
        
        Examples:
            - instruct="male" → male voice
            - instruct="female, young adult" → young female
            - instruct="male, elderly, low pitch, whisper" → whispering old man
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            "Synthesizing %d chars with custom instruct: %s",
            len(text),
            instruct,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._omnivoice_url}/synthesize",
                json={
                    "text": text,
                    "voice": instruct,
                    "language": language,
                },
            )
            
            if response.status_code != 200:
                raise RuntimeError(
                    f"OmniVoice synthesize error: {response.status_code} - {response.text}"
                )
            
            output_path.write_bytes(response.content)

        logger.info("OmniVoice synthesis complete: %s", output_path)
        return output_path

    async def health_check(self) -> bool:
        """Check if OmniVoice server is healthy."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._omnivoice_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OmniVoice health check failed: {e}")
            return False

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
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        instruct = voice_params.to_instruct_string()
        logger.info(
            "Synthesizing %d chars with Voice Design params: '%s' (language: %s)",
            len(text),
            instruct,
            target_language,
        )

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._omnivoice_url}/synthesize",
                json={
                    "text": text,
                    "voice": instruct,
                    "language": target_language,
                },
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"OmniVoice synthesize error: {response.status_code} - {response.text}"
                )

            output_path.write_bytes(response.content)

        logger.info("OmniVoice synthesis complete: %s", output_path)
        return output_path

    async def synthesize_with_clone(
        self,
        text: str,
        ref_audio_path: Path,
        ref_text: str,
        output_path: Path,
        language: str = None,
    ) -> Path:
        """
        Synthesize speech using Voice Cloning mode.

        The generated voice will match the reference audio speaker.

        Args:
            text: Text to synthesize (translated text)
            ref_audio_path: Path to reference audio for voice cloning
            ref_text: Transcription of the reference audio
            output_path: Where to save the synthesized audio
            language: Target language for correct pronunciation

        Returns:
            Path to the generated audio file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Voice cloning: %d chars | ref_audio: %s | ref_text: %d chars | language: %s",
            len(text),
            ref_audio_path.name,
            len(ref_text),
            language or "auto",
        )

        # Read reference audio and encode as base64
        import base64
        ref_audio_bytes = ref_audio_path.read_bytes()
        ref_audio_base64 = base64.b64encode(ref_audio_bytes).decode('utf-8')

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{self._omnivoice_url}/synthesize_clone_json",
                json={
                    "text": text,
                    "ref_text": ref_text or "",
                    "ref_audio_base64": ref_audio_base64,
                    "language": language,
                },
            )

            if response.status_code != 200:
                raise RuntimeError(
                    f"OmniVoice voice cloning error: {response.status_code} - {response.text}"
                )

            output_path.write_bytes(response.content)

        logger.info("Voice cloning complete: %s", output_path)
        return output_path
