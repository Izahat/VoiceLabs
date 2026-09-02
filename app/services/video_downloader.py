"""
Video Downloader Service — downloads videos from YouTube, TikTok, Instagram using yt-dlp.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Downloads videos from various platforms using yt-dlp."""

    SUPPORTED_PLATFORMS = ["youtube", "tiktok", "instagram"]

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("/tmp/video_downloads")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def download(self, url: str, output_path: Path) -> Path:
        """
        Download video from URL and save to output_path.

        Supports: YouTube, TikTok, Instagram.

        Args:
            url: Video URL
            output_path: Directory or path where to save the video

        Returns:
            Path to the downloaded video file
        """
        if isinstance(output_path, Path) and output_path.is_dir():
            output_file = output_path / "video.mp4"
        else:
            output_file = output_path

        logger.info("Downloading video from: %s", url)

        cmd = [
            "yt-dlp",
            "--output", str(output_file),
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--no-playlist",
            "--no-warnings",
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minutes timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                logger.error("yt-dlp failed: %s", error_msg)
                raise RuntimeError(f"Failed to download video: {error_msg}")

            # yt-dlp might save with different extension, find the actual file
            if output_file.exists():
                logger.info("Video downloaded: %s", output_file)
                return output_file

            # Try to find the downloaded file
            for ext in [".mp4", ".mkv", ".webm", ".mov"]:
                alt_path = output_path / f"video{ext}" if isinstance(output_path, Path) and output_path.is_dir() else Path(str(output_path).replace(".mp4", ext))
                if alt_path.exists():
                    logger.info("Video downloaded: %s", alt_path)
                    return alt_path

            raise RuntimeError("Download succeeded but file not found")

        except subprocess.TimeoutExpired:
            raise RuntimeError("Video download timed out (10 minutes)")
        except FileNotFoundError:
            raise RuntimeError("yt-dlp not found. Install with: pip install yt-dlp")

    async def get_info(self, url: str) -> dict:
        """
        Get video information without downloading.

        Returns metadata like title, duration, uploader, etc.
        """
        cmd = [
            "yt-dlp",
            "--dump-json",
            "--no-download",
            "--no-warnings",
            url,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode != 0:
                raise RuntimeError(f"Failed to get video info: {result.stderr}")

            import json
            info = json.loads(result.stdout)
            return {
                "title": info.get("title"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "upload_date": info.get("upload_date"),
                "thumbnail": info.get("thumbnail"),
                "description": info.get("description"),
            }

        except subprocess.TimeoutExpired:
            raise RuntimeError("Get video info timed out")
        except FileNotFoundError:
            raise RuntimeError("yt-dlp not found")

    def is_supported(self, url: str) -> bool:
        """Check if the URL is from a supported platform."""
        supported_domains = [
            "youtube.com",
            "youtu.be",
            "tiktok.com",
            "instagram.com",
        ]
        return any(domain in url.lower() for domain in supported_domains)