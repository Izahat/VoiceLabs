"""
Dubbing API Router — FastAPI endpoints for the dubbing pipeline.

This is a thin adapter layer. It receives HTTP requests, delegates to
the DubbingOrchestrator (business logic), and returns HTTP responses.
"""

import logging
import shutil
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
import httpx

from app.domain.entities import (
    DubbingJob,
    JobStatus,
    VoiceDesignParams,
    Gender,
    Age,
    Pitch,
    Style,
    Accent,
)
from app.services.dubbing_orchestrator import DubbingOrchestrator
from infrastructure.audio_separator_client import AudioSeparatorClient
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dubbing", tags=["dubbing"])

_orchestrator: DubbingOrchestrator | None = None
_settings = get_settings()


def init_router(orchestrator: DubbingOrchestrator) -> None:
    global _orchestrator
    _orchestrator = orchestrator


def _get_orchestrator() -> DubbingOrchestrator:
    if _orchestrator is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _orchestrator


# ============================================================
# Helper: build VoiceDesignParams from request form fields
# ============================================================


def _build_voice_design_params(
    gender: Optional[str] = None,
    age: Optional[str] = None,
    pitch: Optional[str] = None,
    style: Optional[str] = None,
    accent: Optional[str] = None,
    custom_instruct: Optional[str] = None,
) -> Optional[VoiceDesignParams]:
    """Build VoiceDesignParams if any voice design field is set."""
    if all(v is None for v in [gender, age, pitch, style, accent, custom_instruct]):
        return None

    return VoiceDesignParams(
        gender=Gender(gender) if gender else None,
        age=Age(age) if age else None,
        pitch=Pitch(pitch) if pitch else None,
        style=Style(style) if style else None,
        accent=Accent(accent) if accent else None,
        custom_instruct=custom_instruct,
    )


# ============================================================
# Endpoints
# ============================================================


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/languages")
async def list_languages():
    """Proxy to OmniVoice /languages endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{_settings.omnivoice_url}/languages")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch languages from OmniVoice: %s", exc)
        # Return a fallback list of common languages
        return {
            "languages": [
                {"code": "en", "name": "English"},
                {"code": "ru", "name": "Russian"},
                {"code": "tr", "name": "Turkish"},
                {"code": "zh", "name": "Chinese"},
                {"code": "ja", "name": "Japanese"},
                {"code": "ko", "name": "Korean"},
                {"code": "es", "name": "Spanish"},
                {"code": "fr", "name": "French"},
                {"code": "de", "name": "German"},
                {"code": "it", "name": "Italian"},
                {"code": "pt", "name": "Portuguese"},
                {"code": "ar", "name": "Arabic"},
                {"code": "hi", "name": "Hindi"},
                {"code": "uk", "name": "Ukrainian"},
                {"code": "az", "name": "Azerbaijani"},
                {"code": "fa", "name": "Persian"},
            ]
        }


@router.get("/voices")
async def list_voices():
    """Proxy to OmniVoice /voices endpoint."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{_settings.omnivoice_url}/voices")
            resp.raise_for_status()
            return resp.json()
    except Exception as exc:
        logger.warning("Failed to fetch voices from OmniVoice: %s", exc)
        return {
            "voices": [
                {"id": "male", "description": "Default male voice"},
                {"id": "female", "description": "Default female voice"},
            ]
        }


@router.post("/process")
async def process_video(
    video: UploadFile = File(..., description="Video file to dub"),
    target_language: str = Form(..., description="Target language code (e.g. 'ru', 'tr', 'en')"),
    source_language: Optional[str] = Form(None, description="Source language code (auto-detect if omitted)"),
    # Voice Design params (all optional)
    gender: Optional[str] = Form(None, description="Gender: 'male' or 'female'"),
    age: Optional[str] = Form(None, description="Age: 'child', 'teenager', 'young adult', 'middle-aged', 'elderly'"),
    pitch: Optional[str] = Form(None, description="Pitch: 'very low pitch', 'low pitch', 'moderate pitch', 'high pitch', 'very high pitch'"),
    style: Optional[str] = Form(None, description="Style: 'whisper'"),
    accent: Optional[str] = Form(None, description="Accent: 'american accent', 'british accent', etc."),
    custom_instruct: Optional[str] = Form(None, description="Custom voice instruct string (overrides all other fields)"),
):
    """
    Submit a video for dubbing with optional Voice Design parameters.

    If any voice_design field is set, uses explicit voice attributes (gender, age,
    pitch, style, accent). Otherwise falls back to language-guided defaults.
    """
    orchestrator = _get_orchestrator()
    settings = _settings

    job = DubbingJob(target_language=target_language)
    job_temp = settings.temp_dir / job.id
    job_temp.mkdir(parents=True, exist_ok=True)

    input_path = job_temp / video.filename
    with input_path.open("wb") as f:
        shutil.copyfileobj(video.file, f)
    job.input_video_path = input_path

    voice_params = _build_voice_design_params(
        gender=gender,
        age=age,
        pitch=pitch,
        style=style,
        accent=accent,
        custom_instruct=custom_instruct,
    )

    if voice_params:
        logger.info(
            "Processing job %s with Voice Design: %s",
            job.id,
            voice_params.to_instruct_string(),
        )
        job = await orchestrator.process_with_voice_design(job, voice_params)
    else:
        logger.info("Processing job %s with language-guided voice defaults", job.id)
        job = await orchestrator.process(job)

    shutil.rmtree(job_temp, ignore_errors=True)

    if job.status == JobStatus.COMPLETED:
        return {
            "job_id": job.id,
            "status": job.status.value,
            "transcription": {
                "language": job.transcription.language,
                "full_text": job.transcription.full_text,
                "segments": [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in job.transcription.segments
                ],
            },
            "translation": {
                "source_language": job.translation.source_language,
                "target_language": job.translation.target_language,
                "original_text": job.translation.original_text,
                "translated_text": job.translation.translated_text,
            },
            "output_video": f"/api/v1/dubbing/output/{job.id}",
            "voice_design": voice_params.to_instruct_string() if voice_params else None,
        }
    else:
        raise HTTPException(status_code=500, detail=job.error_message or "Pipeline failed")


@router.post("/process/download")
async def process_video_download(
    video: UploadFile = File(..., description="Video file to dub"),
    target_language: str = Form(...),
    source_language: Optional[str] = Form(None),
    gender: Optional[str] = Form(None),
    age: Optional[str] = Form(None),
    pitch: Optional[str] = Form(None),
    style: Optional[str] = Form(None),
    accent: Optional[str] = Form(None),
    custom_instruct: Optional[str] = Form(None),
):
    """Same as /process but returns the dubbed video as a downloadable MP4."""
    orchestrator = _get_orchestrator()
    settings = _settings

    job = DubbingJob(target_language=target_language)
    job_temp = settings.temp_dir / job.id
    job_temp.mkdir(parents=True, exist_ok=True)

    input_path = job_temp / video.filename
    with input_path.open("wb") as f:
        shutil.copyfileobj(video.file, f)
    job.input_video_path = input_path

    voice_params = _build_voice_design_params(
        gender=gender, age=age, pitch=pitch, style=style, accent=accent, custom_instruct=custom_instruct
    )

    if voice_params:
        job = await orchestrator.process_with_voice_design(job, voice_params)
    else:
        job = await orchestrator.process(job)

    shutil.rmtree(job_temp, ignore_errors=True)

    if job.status != JobStatus.COMPLETED or not job.output_video_path:
        raise HTTPException(status_code=500, detail=job.error_message or "Pipeline failed")

    return FileResponse(
        path=job.output_video_path,
        filename=f"dubbed_{job.id}.mp4",
        media_type="video/mp4",
    )


@router.post("/clone")
async def clone_video(
    reference_audio: UploadFile = File(..., description="Reference audio or video for voice cloning"),
    target_language: str = Form(..., description="Target language code"),
    source_language: Optional[str] = Form(None),
    text: Optional[str] = Form(None, description="Optional text for pronunciation guide"),
    text_language: Optional[str] = Form(None, description="Language of the provided text"),
):
    """
    Submit audio or video for voice cloning and translation.

    The uploaded file (audio or video) is processed to extract clean vocals,
    then used as reference for voice cloning with OmniVoice.
    """
    orchestrator = _get_orchestrator()
    settings = _settings

    job = DubbingJob(target_language=target_language)
    job_temp = settings.temp_dir / job.id
    job_temp.mkdir(parents=True, exist_ok=True)

    # Save the reference file (audio or video)
    ref_path = job_temp / reference_audio.filename
    with ref_path.open("wb") as f:
        shutil.copyfileobj(reference_audio.file, f)

    job = await orchestrator.process_with_cloning(
        job,
        reference_audio_path=ref_path,
        text=text,
        text_language=text_language,
    )
    shutil.rmtree(job_temp, ignore_errors=True)

    if job.status == JobStatus.COMPLETED:
        return {
            "job_id": job.id,
            "status": job.status.value,
            "transcription": {
                "language": job.transcription.language,
                "full_text": job.transcription.full_text,
            },
            "translation": {
                "source_language": job.translation.source_language,
                "target_language": job.translation.target_language,
                "translated_text": job.translation.translated_text,
            },
            "output_audio": f"/api/v1/dubbing/output/{job.id}",
        }
    else:
        raise HTTPException(status_code=500, detail=job.error_message or "Voice cloning pipeline failed")


@router.post("/clone/download")
async def clone_video_download(
    reference_audio: UploadFile = File(...),
    target_language: str = Form(...),
    source_language: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    text_language: Optional[str] = Form(None),
):
    """Same as /clone but returns the result as a downloadable file."""
    orchestrator = _get_orchestrator()
    settings = _settings

    job = DubbingJob(target_language=target_language)
    job_temp = settings.temp_dir / job.id
    job_temp.mkdir(parents=True, exist_ok=True)

    ref_path = job_temp / reference_audio.filename
    with ref_path.open("wb") as f:
        shutil.copyfileobj(reference_audio.file, f)

    job = await orchestrator.process_with_cloning(
        job,
        reference_audio_path=ref_path,
        text=text,
        text_language=text_language,
    )
    shutil.rmtree(job_temp, ignore_errors=True)

    if job.status != JobStatus.COMPLETED or not job.output_video_path:
        raise HTTPException(status_code=500, detail=job.error_message or "Voice cloning pipeline failed")

    return FileResponse(
        path=job.output_video_path,
        filename=f"cloned_{job.id}.mp4",
        media_type="video/mp4",
    )


@router.get("/output/{job_id}")
async def get_output_video(job_id: str):
    """Serve the output video for a completed job."""
    settings = _settings
    # Look for the file in output_dir
    dubbed_path = settings.output_dir / f"dubbed_{job_id}.mp4"
    cloned_path = settings.output_dir / f"cloned_{job_id}.mp4"

    if dubbed_path.exists():
        return FileResponse(path=dubbed_path, media_type="video/mp4")
    elif cloned_path.exists():
        return FileResponse(path=cloned_path, media_type="video/mp4")
    else:
        raise HTTPException(status_code=404, detail="Output video not found")


# ============================================================
# TTS Endpoints — Text Mode Voice Cloning
# ============================================================

@router.post("/tts/clone")
async def clone_voice(
    reference_audio: UploadFile = File(..., description="Reference audio or video for voice cloning"),
    mode: str = Form("clone", description="Mode: 'clone'"),
):
    """
    Clone a voice from reference audio or video.
    If a video is provided, audio is extracted and clean vocals are separated
    before cloning for maximum accuracy.
    Returns a voice_id that can be used for synthesis.
    """
    orchestrator = _get_orchestrator()
    settings = _settings

    job_temp = settings.temp_dir / f"clone_{id(reference_audio.file)}"
    job_temp.mkdir(parents=True, exist_ok=True)

    ref_audio_path = job_temp / reference_audio.filename
    with ref_audio_path.open("wb") as f:
        shutil.copyfileobj(reference_audio.file, f)

    # If the file is a video, extract audio first
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
    if ref_audio_path.suffix.lower() in video_exts:
        from infrastructure.ffmpeg_audio_mixer import FFmpegAudioMixer
        mixer = FFmpegAudioMixer(settings.ffmpeg_path)
        extracted_audio = job_temp / "ref_extracted_audio.wav"
        ref_audio_path = await mixer.extract_audio(
            video_path=ref_audio_path,
            output_audio_path=extracted_audio,
        )

    # Try to separate vocals for cleaner voice clone
    try:
        separator = AudioSeparatorClient()
        if await separator.health_check():
            vocals_path = job_temp / "ref_vocals.wav"
            ref_audio_path = await separator.separate_vocals(ref_audio_path, vocals_path)
            logger.info("Vocals separated successfully for voice cloning")
    except Exception as e:
        logger.warning("Vocal separation failed, using original audio: %s", e)

    voice_id = await orchestrator.clone_voice(ref_audio_path)

    shutil.rmtree(job_temp, ignore_errors=True)

    return {"voice_id": voice_id, "status": "cloned"}


@router.post("/tts/synthesize")
async def synthesize_text(
    text: str = Body(..., description="Text to synthesize"),
    voice_id: str = Body(..., description="Voice ID from clone endpoint"),
    language: str = Body(None, description="Target language for synthesis"),
):
    """
    Synthesize text using a cloned voice.
    """
    orchestrator = _get_orchestrator()

    audio_path = await orchestrator.synthesize_with_voice_id(text, voice_id, language)

    return {"audio_url": f"http://localhost:8000/api/v1/dubbing/tts/audio/{voice_id}", "status": "ready"}


@router.get("/tts/audio/{voice_id}")
async def get_tts_audio(voice_id: str):
    """Serve the synthesized audio for a voice_id."""
    settings = _settings
    audio_path = settings.output_dir / f"tts_{voice_id}.mp3"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(path=audio_path, media_type="audio/mpeg")


@router.post("/tts/voice-design")
async def voice_design_synthesize(
    text: str = Body(..., description="Text to synthesize"),
    language: str = Body(..., description="Language code (e.g. 'en', 'ru')"),
    gender: Optional[str] = Body(None),
    age: Optional[str] = Body(None),
    pitch: Optional[str] = Body(None),
    style: Optional[str] = Body(None),
    accent: Optional[str] = Body(None),
    custom_instruct: Optional[str] = Body(None),
):
    """
    Synthesize speech using Voice Design parameters (no reference audio needed).

    The user provides text, language, and optional voice attributes.
    OmniVoice generates speech with the specified voice characteristics.
    """
    import uuid

    orchestrator = _get_orchestrator()
    settings = _settings

    voice_params = _build_voice_design_params(
        gender=gender, age=age, pitch=pitch,
        style=style, accent=accent, custom_instruct=custom_instruct,
    )

    if not voice_params:
        voice_params = VoiceDesignParams()

    uid = uuid.uuid4().hex[:12]
    output_path = settings.output_dir / f"vd_{uid}.wav"

    audio_path = await orchestrator.synthesize_with_voice_design(
        text=text,
        voice_params=voice_params,
        language=language,
        output_path=output_path,
    )

    return {
        "id": uid,
        "audio_url": f"/api/v1/dubbing/tts/vd-audio/{uid}",
        "status": "ready",
    }


@router.get("/tts/vd-audio/{uid}")
async def get_voice_design_audio(uid: str):
    """Serve audio generated by Voice Design."""
    settings = _settings
    audio_path = settings.output_dir / f"vd_{uid}.wav"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(path=audio_path, media_type="audio/wav")