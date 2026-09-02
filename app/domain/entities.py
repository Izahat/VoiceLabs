"""
Domain entities — pure data structures with no infrastructure dependencies.
These represent the core business concepts of the dubbing pipeline.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class JobStatus(str, Enum):
    """Lifecycle states of a dubbing job."""

    PENDING = "pending"
    EXTRACTING_AUDIO = "extracting_audio"
    TRANSCRIBING = "transcribing"
    TRANSLATING = "translating"
    SEPARATING_VOCALES = "separating_vocals"  # Voice/music separation
    SYNTHESIZING = "synthesizing"
    MERGING = "merging"
    COMPLETED = "completed"
    FAILED = "failed"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class Age(str, Enum):
    CHILD = "child"
    TEENAGER = "teenager"
    YOUNG_ADULT = "young adult"
    MIDDLE_AGED = "middle-aged"
    ELDERLY = "elderly"


class Pitch(str, Enum):
    VERY_LOW = "very low pitch"
    LOW = "low pitch"
    MODERATE = "moderate pitch"
    HIGH = "high pitch"
    VERY_HIGH = "very high pitch"


class Style(str, Enum):
    WHISPER = "whisper"


class Accent(str, Enum):
    AMERICAN = "american accent"
    BRITISH = "british accent"
    AUSTRALIAN = "australian accent"
    CANADIAN = "canadian accent"
    INDIAN = "indian accent"
    CHINESE = "chinese accent"
    KOREAN = "korean accent"
    JAPANESE = "japanese accent"
    PORTUGUESE = "portuguese accent"
    RUSSIAN = "russian accent"


@dataclass(frozen=True)
class VoiceDesignParams:
    """
    Voice Design parameters — controls the synthesized voice attributes.
    All fields are optional; defaults are determined by the TTS service.
    """

    gender: Optional[Gender] = None
    age: Optional[Age] = None
    pitch: Optional[Pitch] = None
    style: Optional[Style] = None
    accent: Optional[Accent] = None
    custom_instruct: Optional[str] = None  # overrides all other fields if set

    def to_instruct_string(self) -> str:
        """Build a comma-separated voice instruct string."""
        if self.custom_instruct:
            return self.custom_instruct

        parts = []
        if self.gender:
            parts.append(self.gender.value)
        if self.age:
            parts.append(self.age.value)
        if self.pitch:
            parts.append(self.pitch.value)
        if self.style:
            parts.append(self.style.value)
        if self.accent:
            parts.append(self.accent.value)

        return ", ".join(parts) if parts else "female"


@dataclass(frozen=True)
class TranscriptionSegment:
    """A single timed segment of transcribed speech."""

    start: float  # seconds
    end: float    # seconds
    text: str


@dataclass(frozen=True)
class TranscriptionResult:
    """Full transcription output from the STT service."""

    segments: list[TranscriptionSegment]
    language: str          # detected source language code (e.g. "en")
    full_text: str         # concatenated text of all segments


@dataclass(frozen=True)
class TranslationResult:
    """Translated text produced by the LLM."""

    source_language: str
    target_language: str
    original_text: str
    translated_text: str


@dataclass
class DubbingJob:
    """
    Aggregate root that tracks the full lifecycle of a single dubbing request.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: JobStatus = JobStatus.PENDING
    source_language: Optional[str] = None
    target_language: str = ""

    # File paths
    input_video_path: Optional[Path] = None
    extracted_audio_path: Optional[Path] = None
    synthesized_audio_path: Optional[Path] = None
    output_video_path: Optional[Path] = None

    # Intermediate results
    transcription: Optional[TranscriptionResult] = None
    translation: Optional[TranslationResult] = None

    # Error info
    error_message: Optional[str] = None

    def fail(self, message: str) -> None:
        """Transition the job to a failed state with an error description."""
        self.status = JobStatus.FAILED
        self.error_message = message
