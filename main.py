"""
Dublaj — Video Dubbing Pipeline.

Entry point: creates and launches the FastAPI application with all dependencies wired.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import get_settings
from infrastructure.api.dubbing_router import init_router, router as dubbing_router
from infrastructure.api.transcription_router import (
    init_transcription_router,
    router as transcription_router,
)
from app.services.persistence_service import PersistenceService
from app.services.transcription_service import TranscriptionService
from infrastructure.persistence.database import close_db, get_session_factory, init_db
from infrastructure.storage.file_storage import FileStorage
from providers.service_factory import ServiceFactory

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("dublaj")


# ── Application Lifespan ─────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.

    On startup: create all services via the factory and inject into the router.
    On shutdown: cleanup resources if needed.
    """
    settings = get_settings()
    logger.info("Starting VoiceLabs — OmniVoice TTS + Whisper ASR")
    logger.info("Whisper model: %s (device: %s)", settings.whisper_model_repo, settings.whisper_device)
    logger.info("OmniVoice model: %s (device: %s)", settings.omnivoice_model, settings.ai_device)

    # Wire dependencies
    factory = ServiceFactory(settings)
    voice_service = factory.create_voice_service()
    session_factory = get_session_factory(settings)
    await init_db(session_factory)
    persistence = PersistenceService(session_factory, FileStorage(settings.storage_dir))
    init_router(voice_service, persistence)
    init_transcription_router(persistence, TranscriptionService(voice_service.transcriber))

    logger.info("All services initialized — ready to accept requests")
    yield
    await close_db(session_factory)
    logger.info("Shutting down Dublaj")


# ── FastAPI Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="VoiceLabs — ASR and OmniVoice TTS API",
    description=(
        "VoiceLabs: local Whisper Turbo ASR, OmniVoice TTS and voice cloning. "
        "Translation and automatic video dubbing are planned and currently disabled."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dubbing_router)
app.include_router(transcription_router)


# ── Run ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
