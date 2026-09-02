"""Shared direct-runtime helpers for local Hugging Face model inference.

The application follows HybridVoice's model-loading contract: model weights
live in the normal Hugging Face cache (or an explicitly configured cache),
models are loaded lazily, and the actual device is validated before inference.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def configure_huggingface_cache(cache_dir: str | Path | None) -> Path | None:
    """Configure one shared HF cache before importing model libraries."""
    if not cache_dir:
        return None

    cache_path = Path(cache_dir).expanduser().resolve()
    cache_path.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_path.parent))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(cache_path))
    os.environ.setdefault("TRANSFORMERS_CACHE", str(cache_path))
    return cache_path


def cached_snapshot(
    repo_id: str,
    cache_dir: str | Path | None = None,
    token: str | None = None,
) -> Path:
    """Resolve a model repository to a local cached snapshot."""
    cache_path = configure_huggingface_cache(cache_dir)
    from huggingface_hub import snapshot_download

    kwargs = {"repo_id": repo_id}
    if cache_path is not None:
        kwargs["cache_dir"] = str(cache_path)
    if token:
        kwargs["token"] = token
    snapshot_path = snapshot_download(**kwargs)
    logger.info("Using cached model %s from %s", repo_id, snapshot_path)
    return Path(snapshot_path)


def resolve_device(requested: str | None = None) -> str:
    """Return a validated device using CUDA → MPS → CPU auto selection."""
    import torch

    candidate = (requested or "auto").strip().lower()
    if candidate == "auto":
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    if candidate in {"cuda", "gpu"}:
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA was requested, but torch.cuda.is_available() is False")
        return "cuda"
    if candidate == "mps":
        if not hasattr(torch.backends, "mps") or not torch.backends.mps.is_available():
            raise RuntimeError("MPS was requested, but it is unavailable")
        return "mps"
    if candidate == "cpu":
        return "cpu"
    raise ValueError("Unsupported device. Use auto, cuda, mps, or cpu")


def resolve_whisper_runtime(
    requested_device: str | None = None,
    requested_compute_type: str | None = None,
) -> tuple[str, str]:
    """Resolve a faster-whisper-compatible device and compute type."""
    requested = (requested_device or "auto").strip().lower()
    device = resolve_device(requested)
    if device == "mps":
        logger.info("faster-whisper does not use MPS directly; falling back to CPU")
        device = "cpu"

    compute_type = (requested_compute_type or "auto").strip().lower()
    if compute_type == "auto":
        compute_type = "float16" if device == "cuda" else "int8"
    if device == "cpu" and compute_type == "float16":
        logger.info("faster-whisper CPU runtime does not use float16; selecting int8")
        compute_type = "int8"
    return device, compute_type
