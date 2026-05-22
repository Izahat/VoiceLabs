"""
LLM Translator — translates text using a configurable AI model (Google Gemini).

Implements ITranslator. The provider and model are fully configurable via Settings.
Can be swapped for OpenAI, Anthropic, or any other provider by creating a new
ITranslator implementation — zero changes to business logic.
"""

import logging

from google import genai

from app.domain.entities import TranslationResult
from app.domain.interfaces import ITranslator

logger = logging.getLogger(__name__)


class LLMTranslator(ITranslator):
    """
    Translates text via Google Gemini (or compatible) LLM.

    The translation prompt is designed to preserve meaning, tone, and naturalness
    for dubbing/voice-over use cases.
    """

    def __init__(self, api_key: str, model_name: str) -> None:
        self._model_name = model_name
        self._client = genai.Client(api_key=api_key)

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str,
    ) -> TranslationResult:
        """Translate text using the configured LLM."""

        logger.info(
            "Translating %d chars: %s → %s via %s",
            len(text),
            source_language,
            target_language,
            self._model_name,
        )

        prompt = self._build_prompt(text, source_language, target_language)

        response = await self._client.aio.models.generate_content(
            model=self._model_name,
            contents=prompt,
        )

        translated_text = response.text.strip()

        width = 60
        logger.info("╔%s╗", "═" * width)
        logger.info("║  ПЕРЕВОД: %s → %s  (%s)", source_language, target_language, self._model_name)
        logger.info("╠%s╣", "═" * width)
        logger.info("║  ОРИГИНАЛ:")
        for line in text.splitlines():
            for chunk in _chunks(line, width - 4):
                logger.info("║  %s", chunk)
        logger.info("╠%s╣", "═" * width)
        logger.info("║  ПЕРЕВОД:")
        for line in translated_text.splitlines():
            for chunk in _chunks(line, width - 4):
                logger.info("║  %s", chunk)
        logger.info("╠%s╣", "═" * width)
        logger.info("║  Символов: %d → %d", len(text), len(translated_text))
        logger.info("╚%s╝", "═" * width)

        return TranslationResult(
            source_language=source_language,
            target_language=target_language,
            original_text=text,
            translated_text=translated_text,
        )

    @staticmethod
    def _build_prompt(text: str, source_language: str, target_language: str) -> str:
        """Build a translation prompt optimized for dubbing/voice-over."""
        return (
            f"You are a professional translator specializing in video dubbing.\n"
            f"Translate the following text from {source_language} to {target_language}.\n\n"
            f"Rules:\n"
            f"- Preserve the original meaning, tone, and emotion.\n"
            f"- Make the translation sound natural for spoken voice-over.\n"
            f"- Keep the sentence structure suitable for lip-sync (similar length).\n"
            f"- Do NOT add any explanations, notes, or commentary.\n"
            f"- Return ONLY the translated text.\n\n"
            f"Text to translate:\n{text}"
        )


def _chunks(text: str, max_len: int) -> list[str]:
    """Split text into lines that fit within max_len characters."""
    if not text:
        return [""]
    parts = []
    while len(text) > max_len:
        cut = text[:max_len].rfind(" ")
        if cut == -1:
            cut = max_len
        parts.append(text[:cut])
        text = text[cut:].lstrip()
    if text:
        parts.append(text)
    return parts
