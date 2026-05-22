"""
Dubbing Orchestrator — the core business-logic service.

Coordinates the full pipeline:
  Video → Extract Audio → Transcribe → Translate → TTS (voice clone) → Merge → Output

This service has ZERO knowledge of concrete infrastructure.
All dependencies are injected via interfaces.
"""

import logging
import shutil
from pathlib import Path

from app.domain.entities import DubbingJob, JobStatus, VoiceDesignParams
from app.domain.interfaces import IAudioMixer, ITranscriber, ITranslator, ITTSSynthesizer, IVoiceSeparator

logger = logging.getLogger(__name__)


class DubbingOrchestrator:
    """
    Orchestrates the end-to-end video dubbing pipeline.

    Single Responsibility: manage the pipeline flow and job state transitions.
    Open/Closed: new steps can be added without modifying existing logic.
    Dependency Inversion: depends only on abstract interfaces.
    """

    def __init__(
        self,
        transcriber: ITranscriber,
        translator: ITranslator,
        tts_synthesizer: ITTSSynthesizer,
        audio_mixer: IAudioMixer,
        voice_separator: IVoiceSeparator,
        use_voice_separation: bool,
        temp_dir: Path,
        output_dir: Path,
    ) -> None:
        self._transcriber = transcriber
        self._translator = translator
        self._tts = tts_synthesizer
        self._mixer = audio_mixer
        self._voice_separator = voice_separator
        self._use_voice_separation = use_voice_separation
        self._temp_dir = temp_dir
        self._output_dir = output_dir

    async def process(self, job: DubbingJob) -> DubbingJob:
        """
        Execute the full dubbing pipeline for a given job.

        Args:
            job: A DubbingJob with input_video_path and target_language set.

        Returns:
            The same DubbingJob updated with results or error info.
        """
        try:
            # Ensure working directories exist
            self._temp_dir.mkdir(parents=True, exist_ok=True)
            self._output_dir.mkdir(parents=True, exist_ok=True)

            job_temp = self._temp_dir / job.id
            job_temp.mkdir(parents=True, exist_ok=True)

            # ── Step 1: Extract audio from video and create mute video ───
            job.status = JobStatus.EXTRACTING_AUDIO
            logger.info("Job %s — extracting audio from video", job.id)

            extracted_audio = job_temp / "original_audio.wav"
            job.extracted_audio_path = await self._mixer.extract_audio(
                video_path=job.input_video_path,
                output_audio_path=extracted_audio,
            )

            mute_video = job_temp / "mute_video.mp4"
            mute_video_path = await self._mixer.create_mute_video(
                video_path=job.input_video_path,
                output_video_path=mute_video,
            )

            # ── Step 2: Transcribe audio via Whisper ─────────────────────
            job.status = JobStatus.TRANSCRIBING
            logger.info("Job %s — transcribing audio", job.id)

            job.transcription = await self._transcriber.transcribe(
                audio_path=job.extracted_audio_path,
            )
            logger.info(
                "Job %s — detected language: %s, segments: %d",
                job.id,
                job.transcription.language,
                len(job.transcription.segments),
            )

            # ── Step 3: Translate text via AI model ──────────────────────
            job.status = JobStatus.TRANSLATING
            logger.info("Job %s — translating to %s", job.id, job.target_language)

            job.translation = await self._translator.translate(
                text=job.transcription.full_text,
                source_language=job.transcription.language,
                target_language=job.target_language,
            )

            # ── Step 4: Synthesize voice-cloned audio via TTS ────────────
            job.status = JobStatus.SYNTHESIZING
            logger.info("Job %s — synthesizing dubbed audio with voice cloning", job.id)

            synthesized_audio = job_temp / "dubbed_audio.wav"
            job.synthesized_audio_path = await self._tts.synthesize(
                text=job.translation.translated_text,
                reference_audio_path=job.extracted_audio_path,
                reference_text=job.transcription.full_text,
                target_language=job.target_language,
                output_path=synthesized_audio,
            )

            # ── Step 5: Merge new audio into video ───────────────────────
            job.status = JobStatus.MERGING
            logger.info("Job %s — merging dubbed audio into video", job.id)

            output_video = self._output_dir / f"dubbed_{job.id}.mp4"
            job.output_video_path = await self._mixer.merge_audio_into_video(
                video_path=mute_video_path,
                audio_path=job.synthesized_audio_path,
                output_video_path=output_video,
            )

            # ── Done ─────────────────────────────────────────────────────
            job.status = JobStatus.COMPLETED
            logger.info("Job %s — completed successfully: %s", job.id, job.output_video_path)

        except Exception as exc:
            logger.exception("Job %s — pipeline failed", job.id)
            job.fail(str(exc))

        return job

    async def process_with_voice_design(
        self, job: DubbingJob, voice_params: VoiceDesignParams
    ) -> DubbingJob:
        """
        Execute the dubbing pipeline with explicit Voice Design parameters.

        Unlike process() which uses language-guided defaults, this method
        allows full control over gender, age, pitch, accent, and style.

        Args:
            job: A DubbingJob with input_video_path and target_language set.
            voice_params: Voice attributes for the synthesized voice.

        Returns:
            The same DubbingJob updated with results or error info.
        """
        try:
            self._temp_dir.mkdir(parents=True, exist_ok=True)
            self._output_dir.mkdir(parents=True, exist_ok=True)

            job_temp = self._temp_dir / job.id
            job_temp.mkdir(parents=True, exist_ok=True)

            # ── Step 1: Extract audio ─────────────────────────────────────
            job.status = JobStatus.EXTRACTING_AUDIO
            logger.info(
                "Job %s — extracting audio (Voice Design: %s)",
                job.id,
                voice_params.to_instruct_string(),
            )

            extracted_audio = job_temp / "original_audio.wav"
            job.extracted_audio_path = await self._mixer.extract_audio(
                video_path=job.input_video_path,
                output_audio_path=extracted_audio,
            )

            mute_video = job_temp / "mute_video.mp4"
            mute_video_path = await self._mixer.create_mute_video(
                video_path=job.input_video_path,
                output_video_path=mute_video,
            )

            # ── Step 2: Transcribe ────────────────────────────────────────
            job.status = JobStatus.TRANSCRIBING
            logger.info("Job %s — transcribing audio", job.id)

            job.transcription = await self._transcriber.transcribe(
                audio_path=job.extracted_audio_path,
            )

            # ── Step 3: Translate ─────────────────────────────────────────
            job.status = JobStatus.TRANSLATING
            logger.info("Job %s — translating to %s", job.id, job.target_language)

            job.translation = await self._translator.translate(
                text=job.transcription.full_text,
                source_language=job.transcription.language,
                target_language=job.target_language,
            )

            # ── Step 4: Synthesize with Voice Design params ───────────────
            job.status = JobStatus.SYNTHESIZING
            logger.info("Job %s — synthesizing with Voice Design: %s", job.id, voice_params.to_instruct_string())

            synthesized_audio = job_temp / "dubbed_audio.wav"
            job.synthesized_audio_path = await self._tts.synthesize_with_params(
                text=job.translation.translated_text,
                voice_params=voice_params,
                target_language=job.target_language,
                output_path=synthesized_audio,
            )

            # ── Step 5: Merge ──────────────────────────────────────────────
            job.status = JobStatus.MERGING
            logger.info("Job %s — merging dubbed audio into video", job.id)

            output_video = self._output_dir / f"dubbed_{job.id}.mp4"
            job.output_video_path = await self._mixer.merge_audio_into_video(
                video_path=mute_video_path,
                audio_path=job.synthesized_audio_path,
                output_video_path=output_video,
            )

            # ── Done ───────────────────────────────────────────────────────
            job.status = JobStatus.COMPLETED
            logger.info("Job %s — Voice Design completed: %s", job.id, job.output_video_path)

        except Exception as exc:
            logger.exception("Job %s — Voice Design pipeline failed", job.id)
            job.fail(str(exc))

        return job

    # Video file extensions for detecting whether reference is a video
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}

    def _is_video_file(self, path: Path) -> bool:
        return path.suffix.lower() in self.VIDEO_EXTENSIONS

    async def _extract_clean_vocals(self, audio_path: Path, job_temp: Path, prefix: str = "ref") -> Path:
        """
        Extract clean vocals from an audio file.

        If voice separation is enabled, runs vocal separation to remove
        background music/noise. Otherwise returns the original audio.
        """
        if not self._use_voice_separation:
            logger.info("Voice separation disabled, using original audio as reference")
            return audio_path

        logger.info("Separating vocals from: %s", audio_path.name)
        clean_vocals = job_temp / f"{prefix}_clean_vocals.wav"
        return await self._voice_separator.separate_vocals(
            audio_path=audio_path,
            output_path=clean_vocals,
        )

    async def _prepare_reference_audio(self, ref_path: Path, job_temp: Path, prefix: str = "ref") -> Path:
        """
        Prepare a reference file for voice cloning.

        If the file is a video, extracts audio first.
        Then separates clean vocals (if voice separation is enabled).

        Returns path to clean audio ready for voice cloning.
        """
        audio_path = ref_path

        # Step 1: If video, extract audio
        if self._is_video_file(ref_path):
            logger.info("Reference is a video file, extracting audio: %s", ref_path.name)
            extracted = job_temp / f"{prefix}_extracted_audio.wav"
            audio_path = await self._mixer.extract_audio(
                video_path=ref_path,
                output_audio_path=extracted,
            )

        # Step 2: Separate clean vocals
        return await self._extract_clean_vocals(audio_path, job_temp, prefix)

    async def process_with_cloning(
        self,
        job: DubbingJob,
        reference_audio_path: Path = None,
        text: str = None,
        text_language: str = None,
    ) -> DubbingJob:
        """
        Execute voice cloning pipeline from a reference audio/video file.

        The reference file is processed to extract clean vocals (if video,
        audio is extracted first). Clean vocals are used for voice cloning.

        Args:
            job: A DubbingJob with target_language set.
            reference_audio_path: Path to a reference audio or video file.
            text: Optional text to use for translation.
            text_language: Language of the provided text.

        Returns:
            The same DubbingJob updated with results or error info.
        """
        try:
            # Ensure working directories exist
            self._temp_dir.mkdir(parents=True, exist_ok=True)
            self._output_dir.mkdir(parents=True, exist_ok=True)

            job_temp = self._temp_dir / job.id
            job_temp.mkdir(parents=True, exist_ok=True)

            if not reference_audio_path:
                raise ValueError("reference_audio_path is required for voice cloning")

            # ── Step 1: Prepare reference audio (extract from video + clean vocals) ──
            job.status = JobStatus.SEPARATING_VOCALES
            logger.info("Job %s — preparing reference: %s", job.id, reference_audio_path.name)

            ref_audio_path = await self._prepare_reference_audio(
                reference_audio_path, job_temp, prefix="clone_ref"
            )

            # ── Step 2: Transcribe reference audio ──────────────────────
            job.status = JobStatus.TRANSCRIBING
            logger.info("Job %s — transcribing reference audio", job.id)

            job.transcription = await self._transcriber.transcribe(
                audio_path=ref_audio_path,
            )
            logger.info(
                "Job %s — detected language: %s, segments: %d",
                job.id,
                job.transcription.language,
                len(job.transcription.segments),
            )

            # ── Step 3: Translate text ──────────────────────────────────
            source_text = text if text else job.transcription.full_text
            source_lang = text_language if text_language else job.transcription.language
            ref_text = job.transcription.full_text

            job.status = JobStatus.TRANSLATING
            logger.info("Job %s — translating to %s", job.id, job.target_language)

            job.translation = await self._translator.translate(
                text=source_text,
                source_language=source_lang,
                target_language=job.target_language,
            )

            # ── Step 4: Synthesize with VOICE CLONING ────────────────────
            job.status = JobStatus.SYNTHESIZING
            logger.info("Job %s — synthesizing with VOICE CLONING (ref: %s)", job.id, ref_audio_path.name)

            synthesized_audio = job_temp / "cloned_audio.wav"
            job.synthesized_audio_path = await self._tts.synthesize_with_clone(
                text=job.translation.translated_text,
                ref_audio_path=ref_audio_path,
                ref_text=ref_text,
                output_path=synthesized_audio,
            )

            # ── Step 5: Save output ──────────────────────────────────────
            job.status = JobStatus.MERGING
            output_path = self._output_dir / f"cloned_{job.id}.wav"
            import shutil as _shutil
            _shutil.copy2(job.synthesized_audio_path, output_path)
            job.output_video_path = output_path

            # ── Done ─────────────────────────────────────────────────────
            job.status = JobStatus.COMPLETED
            logger.info("Job %s — VOICE CLONING completed: %s", job.id, job.output_video_path)

        except Exception as exc:
            logger.exception("Job %s — voice cloning pipeline failed", job.id)
            job.fail(str(exc))

        return job

    async def clone_voice(self, ref_audio_path: Path) -> str:
        """
        Clone a voice from reference audio and return a voice_id.
        The cloned voice is stored for later synthesis.
        Also auto-transcribes reference audio for OmniVoice API requirement.
        If voice separation is enabled, extracts clean vocals first.
        """
        import uuid
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir.mkdir(parents=True, exist_ok=True)

        voice_id = uuid.uuid4().hex[:12]
        voice_dir = self._output_dir / f"voice_{voice_id}"
        voice_dir.mkdir(parents=True, exist_ok=True)

        # Prepare clean audio for voice cloning
        clean_audio_path = ref_audio_path
        if self._use_voice_separation:
            logger.info("clone_voice — separating vocals from reference: %s", ref_audio_path.name)
            clean_vocals = voice_dir / "clean_vocals.wav"
            clean_audio_path = await self._voice_separator.separate_vocals(
                audio_path=ref_audio_path,
                output_path=clean_vocals,
            )
            logger.info("clone_voice — clean vocals ready for cloning")

        # Copy clean reference audio to voice storage
        stored_ref = voice_dir / "reference.wav"
        shutil.copy2(clean_audio_path, stored_ref)

        # Auto-transcribe reference audio for OmniVoice API (required field ref_text)
        ref_text = ""
        try:
            result = await self._transcriber.transcribe(stored_ref)
            ref_text = " ".join(seg.text for seg in result.segments)
            logger.info("Reference audio transcribed: %d chars", len(ref_text))
        except Exception as e:
            logger.warning("Failed to transcribe reference audio: %s", e)

        # Store ref_text for later use in synthesis
        ref_text_path = voice_dir / "ref_text.txt"
        ref_text_path.write_text(ref_text)

        logger.info("Voice cloned: %s -> %s", ref_audio_path.name, voice_id)
        return voice_id

    async def synthesize_with_voice_id(self, text: str, voice_id: str, language: str = None) -> Path:
        """
        Synthesize text using a previously cloned voice.

        Args:
            text: Text to synthesize.
            voice_id: ID of the cloned voice.
            language: Target language for correct pronunciation.
        """
        self._output_dir.mkdir(parents=True, exist_ok=True)

        voice_dir = self._output_dir / f"voice_{voice_id}"
        if not voice_dir.exists():
            raise ValueError(f"Voice not found: {voice_id}")

        ref_audio_path = voice_dir / "reference.wav"
        ref_text_path = voice_dir / "ref_text.txt"
        ref_text = ref_text_path.read_text() if ref_text_path.exists() else "a voice"

        output_path = self._output_dir / f"tts_{voice_id}.mp3"

        logger.info(
            "Synthesizing text with cloned voice %s: %d chars (language: %s)",
            voice_id,
            len(text),
            language or "auto",
        )

        result_path = await self._tts.synthesize_with_clone(
            text=text,
            ref_audio_path=ref_audio_path,
            ref_text=ref_text,
            output_path=output_path,
            language=language,
        )

        return result_path

    async def synthesize_with_voice_design(
        self, text: str, voice_params: VoiceDesignParams, language: str, output_path: Path
    ) -> Path:
        """Synthesize speech using Voice Design parameters only (no reference audio)."""
        self._output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "Voice Design synthesis: %d chars, language=%s, params=%s",
            len(text), language, voice_params.to_instruct_string(),
        )

        return await self._tts.synthesize_with_params(
            text=text,
            voice_params=voice_params,
            target_language=language,
            output_path=output_path,
        )
