"""
Dubbing API Router — FastAPI endpoints for the dubbing pipeline.

This is a thin adapter layer. It receives HTTP requests, delegates to
the DubbingOrchestrator (business logic), and returns HTTP responses.
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

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
from app.services.persistence_service import PersistenceService
from app.services.voice_service import VoiceService
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dubbing", tags=["dubbing"])

_voice_service: VoiceService | None = None
_persistence: PersistenceService | None = None
_settings = get_settings()


def init_router(
    voice_service: VoiceService,
    persistence: PersistenceService | None = None,
) -> None:
    global _voice_service, _persistence
    _voice_service = voice_service
    _persistence = persistence


def _get_voice_service() -> VoiceService:
    if _voice_service is None:
        raise HTTPException(status_code=503, detail="Service not initialized")
    return _voice_service


def _disabled_video_dubbing() -> None:
    """Compatibility response while translation/video dubbing is not shipped."""
    raise HTTPException(
        status_code=410,
        detail=(
            "Translation and automatic video dubbing are temporarily disabled. "
            "Use the transcription and OmniVoice TTS endpoints."
        ),
    )


def _get_persistence() -> PersistenceService:
    if _persistence is None:
        raise HTTPException(status_code=503, detail="Persistence not initialized")
    return _persistence


async def _user_id(external_id: str | None) -> str:
    user = await _get_persistence().ensure_user(external_id)
    return user.id


async def _finish_job(job: DubbingJob, user_id: str, *, role: str, filename: str, kind: str) -> dict:
    """Persist a pipeline result and return its durable asset metadata."""
    persistence = _get_persistence()
    try:
        if job.status != JobStatus.COMPLETED or not job.output_video_path:
            await persistence.update_job(
                job.id,
                status=job.status.value,
                error_message=job.error_message,
            )
            raise HTTPException(status_code=500, detail=job.error_message or "Pipeline failed")

        if job.extracted_audio_path and job.extracted_audio_path.exists():
            await persistence.save_existing(
                job.extracted_audio_path,
                user_id=user_id,
                role="extracted_audio",
                original_filename=f"{job.id}.wav",
                job_id=job.id,
            )

        asset = await persistence.save_existing(
            job.output_video_path,
            user_id=user_id,
            role=role,
            original_filename=filename,
            job_id=job.id,
        )
        metadata = {
            "transcription": {
                "language": job.transcription.language if job.transcription else None,
                "text": job.transcription.full_text if job.transcription else None,
            },
            "translation": {
                "source_language": job.translation.source_language if job.translation else None,
                "target_language": job.translation.target_language if job.translation else None,
                "text": job.translation.translated_text if job.translation else None,
            },
        }
        await persistence.update_job(
            job.id,
            status=job.status.value,
            output_asset_id=asset.id,
            metadata=metadata,
        )
        return {"asset": asset, "kind": kind}
    finally:
        shutil.rmtree(_settings.temp_dir / job.id, ignore_errors=True)


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
    return {"status": "ok", "runtime": _get_voice_service().runtime}


@router.get("/languages")
async def list_languages():
    """Return common OmniVoice language codes without a network request."""
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
    """Return OmniVoice voice-design presets without a network request."""
    return {
        "voices": [
            {"id": "male", "description": "Default male voice"},
            {"id": "female", "description": "Default female voice"},
            {"id": "male_young", "description": "Male, young adult"},
            {"id": "female_young", "description": "Female, young adult"},
        ]
    }


@router.post("/process", include_in_schema=False)
async def process_video(
    video: UploadFile = File(..., description="Video file to dub"),
    target_language: str = Form(..., description="Target language code (e.g. 'ru', 'tr', 'en')"),
    source_language: Optional[str] = Form(None, description="Source language code (auto-detect if omitted)"),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
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
    _disabled_video_dubbing()
    orchestrator = _get_voice_service()
    persistence = _get_persistence()
    user_id = await _user_id(external_user_id)
    job = DubbingJob(source_language=source_language, target_language=target_language)
    await persistence.create_job(
        user_id=user_id,
        kind="dubbing",
        status=job.status.value,
        source_language=source_language,
        target_language=target_language,
        job_id=job.id,
    )
    input_asset = await persistence.save_upload(
        video,
        user_id=user_id,
        role="input_video",
        job_id=job.id,
    )
    job.input_video_path = Path(input_asset.path)
    await persistence.update_job(job.id, status=job.status.value, source_asset_id=input_asset.id)
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

    result = await _finish_job(
        job,
        user_id,
        role="output_video",
        filename=f"dubbed_{job.id}.mp4",
        kind="video",
    )
    asset = result["asset"]

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
            "output_video": f"/api/v1/dubbing/assets/{asset.id}",
            "voice_design": voice_params.to_instruct_string() if voice_params else None,
        }


@router.post("/process/download", include_in_schema=False)
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
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Same as /process but returns the dubbed video as a downloadable MP4."""
    _disabled_video_dubbing()
    orchestrator = _get_voice_service()
    persistence = _get_persistence()
    user_id = await _user_id(external_user_id)
    job = DubbingJob(source_language=source_language, target_language=target_language)
    await persistence.create_job(
        user_id=user_id,
        kind="dubbing",
        status=job.status.value,
        source_language=source_language,
        target_language=target_language,
        job_id=job.id,
    )
    input_asset = await persistence.save_upload(
        video,
        user_id=user_id,
        role="input_video",
        job_id=job.id,
    )
    job.input_video_path = Path(input_asset.path)
    await persistence.update_job(job.id, status=job.status.value, source_asset_id=input_asset.id)
    voice_params = _build_voice_design_params(
        gender=gender, age=age, pitch=pitch, style=style, accent=accent, custom_instruct=custom_instruct
    )

    if voice_params:
        job = await orchestrator.process_with_voice_design(job, voice_params)
    else:
        job = await orchestrator.process(job)

    result = await _finish_job(
        job,
        user_id,
        role="output_video",
        filename=f"dubbed_{job.id}.mp4",
        kind="video",
    )
    asset = result["asset"]

    return FileResponse(
        path=asset.path,
        filename=f"dubbed_{job.id}.mp4",
        media_type="video/mp4",
    )


@router.post("/clone", include_in_schema=False)
async def clone_video(
    reference_audio: UploadFile = File(..., description="Reference audio or video for voice cloning"),
    target_language: str = Form(..., description="Target language code"),
    source_language: Optional[str] = Form(None),
    text: Optional[str] = Form(None, description="Optional text for pronunciation guide"),
    text_language: Optional[str] = Form(None, description="Language of the provided text"),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Submit audio or video for voice cloning and translation.

    The uploaded file (audio or video) is processed to extract clean vocals,
    then used as reference for voice cloning with OmniVoice.
    """
    _disabled_video_dubbing()
    orchestrator = _get_voice_service()
    persistence = _get_persistence()
    user_id = await _user_id(external_user_id)
    job = DubbingJob(source_language=source_language, target_language=target_language)
    await persistence.create_job(
        user_id=user_id,
        kind="clone_translation",
        status=job.status.value,
        source_language=source_language,
        target_language=target_language,
        job_id=job.id,
    )
    input_asset = await persistence.save_upload(
        reference_audio,
        user_id=user_id,
        role="voice_reference",
        job_id=job.id,
    )
    await persistence.update_job(job.id, status=job.status.value, source_asset_id=input_asset.id)
    job = await orchestrator.process_with_cloning(
        job,
        reference_audio_path=Path(input_asset.path),
        text=text,
        text_language=text_language,
    )
    result = await _finish_job(
        job,
        user_id,
        role="output_audio",
        filename=f"cloned_{job.id}.wav",
        kind="audio",
    )
    asset = result["asset"]
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
        "output_audio": f"/api/v1/dubbing/assets/{asset.id}",
    }


@router.post("/clone/download", include_in_schema=False)
async def clone_video_download(
    reference_audio: UploadFile = File(...),
    target_language: str = Form(...),
    source_language: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    text_language: Optional[str] = Form(None),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """Same as /clone but returns the result as a downloadable file."""
    _disabled_video_dubbing()
    orchestrator = _get_voice_service()
    persistence = _get_persistence()
    user_id = await _user_id(external_user_id)
    job = DubbingJob(source_language=source_language, target_language=target_language)
    await persistence.create_job(
        user_id=user_id,
        kind="clone_translation",
        status=job.status.value,
        source_language=source_language,
        target_language=target_language,
        job_id=job.id,
    )
    input_asset = await persistence.save_upload(
        reference_audio,
        user_id=user_id,
        role="voice_reference",
        job_id=job.id,
    )
    await persistence.update_job(job.id, status=job.status.value, source_asset_id=input_asset.id)
    job = await orchestrator.process_with_cloning(
        job,
        reference_audio_path=Path(input_asset.path),
        text=text,
        text_language=text_language,
    )
    result = await _finish_job(
        job,
        user_id,
        role="output_audio",
        filename=f"cloned_{job.id}.wav",
        kind="audio",
    )
    asset = result["asset"]

    return FileResponse(
        path=asset.path,
        filename=f"cloned_{job.id}.wav",
        media_type="audio/wav",
    )


@router.get("/output/{job_id}")
async def get_output_video(job_id: str, external_user_id: Optional[str] = Header(None, alias="X-User-Id")):
    """Serve the output video for a completed job."""
    settings = _settings
    persistence = _get_persistence()
    user = await persistence.ensure_user(external_user_id)
    db_job = await persistence.get_job(job_id)
    if db_job and db_job.output_asset_id:
        asset = await persistence.get_asset(db_job.output_asset_id)
        if asset and Path(asset.stored_path).exists():
            return FileResponse(
                path=asset.stored_path,
                filename=asset.original_filename,
                media_type=asset.mime_type or "application/octet-stream",
            )

    # Look for the file in output_dir
    dubbed_path = settings.output_dir / f"dubbed_{job_id}.mp4"
    cloned_path = settings.output_dir / f"cloned_{job_id}.mp4"

    if dubbed_path.exists():
        return FileResponse(path=dubbed_path, media_type="video/mp4")
    elif cloned_path.exists():
        return FileResponse(path=cloned_path, media_type="video/mp4")
    else:
        raise HTTPException(status_code=404, detail="Output video not found")


@router.get("/status/{job_id}")
async def get_job_status(job_id: str, external_user_id: Optional[str] = Header(None, alias="X-User-Id")):
    """Return durable job state for clients that want to poll."""
    persistence = _get_persistence()
    user = await persistence.ensure_user(external_user_id)
    job = await persistence.get_job(job_id)
    if job is None or job.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    response = {
        "job_id": job.id,
        "status": job.status,
        "state": job.status,
        "kind": job.kind,
        "error": job.error_message,
    }
    if job.output_asset_id:
        response["output_url"] = f"/api/v1/dubbing/assets/{job.output_asset_id}"
    return response


@router.get("/jobs")
async def list_jobs(external_user_id: Optional[str] = Header(None, alias="X-User-Id")):
    """List the current user's persisted processing history."""
    persistence = _get_persistence()
    user = await persistence.ensure_user(external_user_id)
    jobs = await persistence.list_jobs(user.id)
    return {
        "jobs": [
            {
                "job_id": job.id,
                "kind": job.kind,
                "status": job.status,
                "source_language": job.source_language,
                "target_language": job.target_language,
                "source_asset_id": job.source_asset_id,
                "output_asset_id": job.output_asset_id,
                "error": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ]
    }


@router.get("/assets/{asset_id}")
async def get_asset(asset_id: str, external_user_id: Optional[str] = Header(None, alias="X-User-Id")):
    """Serve a persisted media asset.

    Asset IDs are random and media URLs must work in native browser audio/video
    elements, which cannot attach the X-User-Id header. Authenticated deployments
    should replace this endpoint with signed URLs.
    """
    persistence = _get_persistence()
    asset = await persistence.get_asset(asset_id)
    if asset is None or not Path(asset.stored_path).exists():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(
        path=asset.stored_path,
        filename=asset.original_filename,
        media_type=asset.mime_type or "application/octet-stream",
    )


# ============================================================
# TTS Endpoints — Text Mode Voice Cloning
# ============================================================

@router.post("/tts/clone")
async def clone_voice(
    reference_audio: UploadFile = File(..., description="Reference audio or video for voice cloning"),
    mode: str = Form("clone", description="Mode: 'clone'"),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Clone a voice from reference audio or video.
    If a video is provided, audio is extracted and clean vocals are separated
    before cloning for maximum accuracy.
    Returns a voice_id that can be used for synthesis.
    """
    voice_service = _get_voice_service()
    settings = _settings
    persistence = _get_persistence()
    user_id = await _user_id(external_user_id)

    job_id = f"clone_{uuid.uuid4().hex}"
    await persistence.create_job(
        user_id=user_id,
        kind="voice_profile",
        status=JobStatus.PENDING.value,
        job_id=job_id,
    )

    input_asset = await persistence.save_upload(
        reference_audio,
        user_id=user_id,
        role="voice_reference",
        job_id=job_id,
    )
    await persistence.update_job(job_id, status=JobStatus.PENDING.value, source_asset_id=input_asset.id)
    job_temp = settings.temp_dir / job_id
    job_temp.mkdir(parents=True, exist_ok=True)

    ref_audio_path = Path(input_asset.path)

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

    try:
        voice_id = await voice_service.clone_voice(ref_audio_path)
        ref_text_path = settings.output_dir / f"voice_{voice_id}" / "ref_text.txt"
        ref_text = ref_text_path.read_text(encoding="utf-8") if ref_text_path.exists() else ""
        await persistence.create_voice_profile(
            user_id=user_id,
            reference_asset_id=input_asset.id,
            reference_text=ref_text,
            profile_id=voice_id,
        )
        await persistence.update_job(job_id, status=JobStatus.COMPLETED.value)
        return {"voice_id": voice_id, "job_id": job_id, "status": "cloned"}
    except Exception as exc:
        await persistence.update_job(
            job_id,
            status=JobStatus.FAILED.value,
            error_message=str(exc),
        )
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        shutil.rmtree(job_temp, ignore_errors=True)


@router.post("/tts/synthesize")
async def synthesize_text(
    text: str = Body(..., description="Text to synthesize"),
    voice_id: str = Body(..., description="Voice ID from clone endpoint"),
    language: str = Body(None, description="Target language for synthesis"),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Synthesize text using a cloned voice.
    """
    voice_service = _get_voice_service()
    persistence = _get_persistence()
    user = await persistence.ensure_user(external_user_id)
    profile = await persistence.get_voice_profile(voice_id)
    if profile is None or profile.user_id != user.id:
        raise HTTPException(status_code=404, detail="Voice profile not found")

    job = await persistence.create_job(
        user_id=user.id,
        kind="tts_synthesis",
        status=JobStatus.SYNTHESIZING.value,
        target_language=language,
        metadata={"voice_id": voice_id},
    )
    try:
        audio_path = await voice_service.synthesize_with_voice_id(text, voice_id, language)
        asset = await persistence.save_existing(
            audio_path,
            user_id=user.id,
            role="tts_output",
            original_filename=f"tts_{voice_id}.wav",
            job_id=job.id,
        )
        await persistence.update_job(
            job.id,
            status=JobStatus.COMPLETED.value,
            output_asset_id=asset.id,
        )
    except Exception as exc:
        await persistence.update_job(job.id, status=JobStatus.FAILED.value, error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {"audio_url": f"/api/v1/dubbing/assets/{asset.id}", "status": "ready"}


@router.get("/tts/audio/{voice_id}")
async def get_tts_audio(voice_id: str):
    """Serve the synthesized audio for a voice_id."""
    settings = _settings
    audio_path = settings.output_dir / f"tts_{voice_id}.wav"
    if not audio_path.exists():
        # Compatibility with files generated before the extension fix.
        audio_path = settings.output_dir / f"tts_{voice_id}.mp3"

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(path=audio_path, media_type="audio/wav")


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
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Synthesize speech using Voice Design parameters (no reference audio needed).

    The user provides text, language, and optional voice attributes.
    OmniVoice generates speech with the specified voice characteristics.
    """
    import uuid

    voice_service = _get_voice_service()
    settings = _settings
    persistence = _get_persistence()
    user_id = await _user_id(external_user_id)

    voice_params = _build_voice_design_params(
        gender=gender, age=age, pitch=pitch,
        style=style, accent=accent, custom_instruct=custom_instruct,
    )

    if not voice_params:
        voice_params = VoiceDesignParams()

    uid = uuid.uuid4().hex[:12]
    output_path = settings.output_dir / f"vd_{uid}.wav"
    job = await persistence.create_job(
        user_id=user_id,
        kind="voice_design",
        status=JobStatus.SYNTHESIZING.value,
        target_language=language,
        metadata={"voice_instruct": voice_params.to_instruct_string()},
    )

    try:
        audio_path = await voice_service.synthesize_with_voice_design(
            text=text,
            voice_params=voice_params,
            language=language,
            output_path=output_path,
        )
        asset = await persistence.save_existing(
            audio_path,
            user_id=user_id,
            role="voice_design_output",
            original_filename=f"vd_{uid}.wav",
            job_id=job.id,
        )
        await persistence.update_job(
            job.id,
            status=JobStatus.COMPLETED.value,
            output_asset_id=asset.id,
        )
    except Exception as exc:
        await persistence.update_job(job.id, status=JobStatus.FAILED.value, error_message=str(exc))
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "id": uid,
        "job_id": job.id,
        "audio_url": f"/api/v1/dubbing/assets/{asset.id}",
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
