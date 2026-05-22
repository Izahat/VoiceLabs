"""
FFmpeg Audio Mixer — extracts audio from video and merges new audio back.

Implements IAudioMixer using ffmpeg subprocess calls.
The ffmpeg binary path is configurable via Settings.
"""

import asyncio
import logging
from pathlib import Path

from app.domain.interfaces import IAudioMixer

logger = logging.getLogger(__name__)


class FFmpegAudioMixer(IAudioMixer):
    """
    Uses ffmpeg to extract and merge audio tracks in video files.

    All paths and the ffmpeg binary itself are configurable — no hardcoding.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self._ffmpeg = ffmpeg_path

    async def extract_audio(self, video_path: Path, output_audio_path: Path) -> Path:
        logger.info("Extracting audio: %s → %s", video_path, output_audio_path)

        cmd = [
            self._ffmpeg,
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            "-y",
            str(output_audio_path),
        ]

        await self._run_ffmpeg(cmd)
        logger.info("Audio extraction complete: %s", output_audio_path)
        return output_audio_path

    async def create_mute_video(self, video_path: Path, output_video_path: Path) -> Path:
        logger.info("Creating mute video: %s → %s", video_path, output_video_path)

        cmd = [
            self._ffmpeg,
            "-i", str(video_path),
            "-c:v", "copy",
            "-an",
            "-y",
            str(output_video_path),
        ]

        await self._run_ffmpeg(cmd)
        logger.info("Mute video created: %s", output_video_path)
        return output_video_path

    async def merge_audio_into_video(
        self,
        video_path: Path,
        audio_path: Path,
        output_video_path: Path,
    ) -> Path:
        logger.info(
            "Merging audio into video: %s + %s → %s",
            video_path,
            audio_path,
            output_video_path,
        )

        cmd = [
            self._ffmpeg,
            "-i", str(video_path),
            "-i", str(audio_path),
            "-c:v", "copy",
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-y",
            str(output_video_path),
        ]

        await self._run_ffmpeg(cmd)
        logger.info("Audio merge complete: %s", output_video_path)
        return output_video_path

    async def _run_ffmpeg(self, cmd: list[str]) -> None:
        """Execute an ffmpeg command asynchronously and handle errors."""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            logger.error("FFmpeg failed (code %d): %s", process.returncode, error_msg)
            raise RuntimeError(f"FFmpeg error (code {process.returncode}): {error_msg}")
