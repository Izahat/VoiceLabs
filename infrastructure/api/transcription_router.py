"""
Transcription API Router — FastAPI endpoints for audio/video transcription with speaker diarization.
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.services.transcription_service import TranscriptionService
from app.services.video_downloader import VideoDownloader
from app.services.persistence_service import PersistenceService
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/transcription", tags=["transcription"])

_settings = get_settings()
_transcription_service: Optional[TranscriptionService] = None
_video_downloader: Optional[VideoDownloader] = None
_persistence: Optional[PersistenceService] = None


def init_transcription_router(
    persistence: PersistenceService,
    transcription_service: Optional[TranscriptionService] = None,
) -> None:
    """Inject shared persistence infrastructure during application startup."""
    global _persistence, _transcription_service
    _persistence = persistence
    if transcription_service is not None:
        _transcription_service = transcription_service


def get_persistence() -> PersistenceService:
    if _persistence is None:
        raise HTTPException(status_code=503, detail="Persistence not initialized")
    return _persistence


def get_transcription_service() -> TranscriptionService:
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service


def get_video_downloader() -> VideoDownloader:
    global _video_downloader
    if _video_downloader is None:
        _video_downloader = VideoDownloader()
    return _video_downloader


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "transcription",
        "runtime": get_transcription_service().runtime,
    }


@router.post("/transcribe")
async def transcribe_file(
    file: UploadFile = File(..., description="Audio or video file to transcribe"),
    language: Optional[str] = Form(None, description="Language code (auto-detect if omitted)"),
    enable_diarization: bool = Form(False, description="Reserved for a future release"),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Transcribe an audio/video file with optional speaker diarization.

    Returns the transcribed text with timestamps and speaker segments.
    """
    persistence = get_persistence()
    user = await persistence.ensure_user(external_user_id)
    job_id = f"transcribe_{uuid.uuid4().hex}"
    await persistence.create_job(
        user_id=user.id,
        kind="transcription",
        status="pending",
        source_language=language,
        metadata={"diarization": False},
        job_id=job_id,
    )

    transcription_service = get_transcription_service()

    job_temp = _settings.temp_dir / job_id
    job_temp.mkdir(parents=True, exist_ok=True)
    input_asset = await persistence.save_upload(
        file,
        user_id=user.id,
        role="input_media",
        job_id=job_id,
    )
    input_path = Path(input_asset.path)
    await persistence.update_job(job_id, status="pending", source_asset_id=input_asset.id)

    try:
        # Extract audio if video
        audio_path = input_path
        video_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v"}
        if input_path.suffix.lower() in video_exts:
            from infrastructure.ffmpeg_audio_mixer import FFmpegAudioMixer
            mixer = FFmpegAudioMixer(_settings.ffmpeg_path)
            audio_path = job_temp / "extracted_audio.wav"
            audio_path = await mixer.extract_audio(
                video_path=input_path,
                output_audio_path=audio_path,
            )
            await persistence.save_existing(
                audio_path,
                user_id=user.id,
                role="extracted_audio",
                original_filename=f"{job_id}.wav",
                job_id=job_id,
            )

        # Transcribe
        logger.info("Starting transcription for: %s", file.filename)
        result = await transcription_service.transcribe(audio_path, language=language)

        # Diarization is intentionally disabled until a validated model is
        # selected and integrated in a future release.
        speakers = None

        await persistence.update_job(job_id, status="completed")
        return {
            "status": "completed",
            "language": result.get("language"),
            "full_text": result.get("text"),
            "segments": result.get("segments", []),
            "speakers": speakers,
            "diarization": {
                "status": "planned",
                "enabled": False,
                "message": "Speaker diarization will be added in a future release.",
            },
            "duration": result.get("duration"),
        }

    except Exception as e:
        logger.error("Transcription error: %s", e)
        await persistence.update_job(job_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(job_temp, ignore_errors=True)


@router.post("/transcribe/url")
async def transcribe_url(
    url: str = Form(..., description="URL to YouTube, Instagram, or TikTok video"),
    language: Optional[str] = Form(None, description="Language code (auto-detect if omitted)"),
    enable_diarization: bool = Form(False, description="Reserved for a future release"),
    external_user_id: Optional[str] = Header(None, alias="X-User-Id"),
):
    """
    Download video from URL and transcribe it with optional speaker diarization.

    Supports YouTube, Instagram, TikTok.
    """
    persistence = get_persistence()
    user = await persistence.ensure_user(external_user_id)
    job_id = f"transcribe_{uuid.uuid4().hex}"
    await persistence.create_job(
        user_id=user.id,
        kind="transcription_url",
        status="pending",
        source_language=language,
        metadata={"url": url, "diarization": False},
        job_id=job_id,
    )

    video_downloader = get_video_downloader()
    transcription_service = get_transcription_service()

    job_temp = _settings.temp_dir / job_id
    job_temp.mkdir(parents=True, exist_ok=True)

    try:
        # Download video
        logger.info("Downloading video from: %s", url)
        video_path = await video_downloader.download(url, job_temp)
        await persistence.save_existing(
            video_path,
            user_id=user.id,
            role="input_video",
            original_filename=video_path.name,
            job_id=job_id,
        )

        # Extract audio
        from infrastructure.ffmpeg_audio_mixer import FFmpegAudioMixer
        mixer = FFmpegAudioMixer(_settings.ffmpeg_path)
        audio_path = job_temp / "audio.wav"
        audio_path = await mixer.extract_audio(video_path=video_path, output_audio_path=audio_path)
        await persistence.save_existing(
            audio_path,
            user_id=user.id,
            role="extracted_audio",
            original_filename=f"{job_id}.wav",
            job_id=job_id,
        )

        # Transcribe
        logger.info("Starting transcription for URL: %s", url)
        result = await transcription_service.transcribe(audio_path, language=language)

        speakers = None

        await persistence.update_job(job_id, status="completed")
        return {
            "status": "completed",
            "url": url,
            "language": result.get("language"),
            "full_text": result.get("text"),
            "segments": result.get("segments", []),
            "speakers": speakers,
            "diarization": {
                "status": "planned",
                "enabled": False,
                "message": "Speaker diarization will be added in a future release.",
            },
            "duration": result.get("duration"),
        }

    except Exception as e:
        logger.error("URL transcription error: %s", e)
        await persistence.update_job(job_id, status="failed", error_message=str(e))
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        shutil.rmtree(job_temp, ignore_errors=True)


async def _merge_speakers_with_transcript(transcript_result: dict, speakers: list) -> dict:
    """Merge speaker segments with transcription segments."""
    if not speakers or not transcript_result.get("segments"):
        return transcript_result

    result = transcript_result.copy()
    segments = result.get("segments", [])

    # Assign speakers to each segment based on timestamps
    for segment in segments:
        start = segment["start"]
        end = segment["end"]

        # Find speaker that covers this segment
        speaker = None
        for spk in speakers:
            spk_start = spk.get("start", 0)
            spk_end = spk.get("end", float("inf"))
            # Check overlap
            if start >= spk_start and end <= spk_end:
                speaker = spk.get("speaker")
                break
            elif start < spk_end and end > spk_start:
                speaker = spk.get("speaker")
                break

        segment["speaker"] = speaker or "UNKNOWN"

    return result


@router.get("/supported-platforms")
async def supported_platforms():
    """Return list of supported video platforms."""
    return {
        "platforms": [
            {"name": "YouTube", "url_pattern": "youtube.com|youtu.be"},
            {"name": "TikTok", "url_pattern": "tiktok.com"},
            {"name": "Instagram", "url_pattern": "instagram.com"},
        ]
    }
