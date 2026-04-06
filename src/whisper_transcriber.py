"""Whisper-based fallback transcription for videos without YouTube captions."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from pathlib import Path

logger = logging.getLogger(__name__)

VALID_MODELS = ("tiny", "base", "small", "medium")
AUDIO_CACHE_DIR = Path(".audio_cache")

_cached_model = None
_cached_model_name: str | None = None


def _get_model(model_name: str):
    """Return a cached WhisperModel, loading it only if the name changed."""
    global _cached_model, _cached_model_name
    if _cached_model is None or _cached_model_name != model_name:
        from faster_whisper import WhisperModel
        _cached_model = WhisperModel(model_name)
        _cached_model_name = model_name
    return _cached_model


def download_audio(video_id: str, output_dir: Path) -> Path:
    """Download audio for a YouTube video as mp3.

    Returns the path to the downloaded file.
    Raises RuntimeError if the download fails.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / f"{video_id}.%(ext)s")
    url = f"https://www.youtube.com/watch?v={video_id}"
    cmd = [
        "yt-dlp", "-x", "--audio-format", "mp3",
        "-o", output_template,
        "--no-warnings",
        url,
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to download audio for {video_id}: {e.stderr}") from e

    audio_path = output_dir / f"{video_id}.mp3"
    if not audio_path.exists():
        raise RuntimeError(f"Audio file not found after download: {audio_path}")
    return audio_path


def transcribe_audio(audio_path: Path, model_name: str) -> str:
    """Transcribe an audio file using faster-whisper.

    Returns the full transcript as a single string.
    """
    model = _get_model(model_name)
    segments, _ = model.transcribe(str(audio_path))
    return " ".join(segment.text.strip() for segment in segments)


def whisper_transcript(
    video_id: str,
    model_name: str,
    status_callback: Callable[[str], None] | None = None,
) -> str | None:
    """Download audio and transcribe with Whisper.

    Returns transcript text, or None if any step fails.
    Always cleans up the audio file.
    """
    if model_name not in VALID_MODELS:
        raise ValueError(f"Invalid Whisper model: {model_name}. Must be one of: {', '.join(VALID_MODELS)}")

    audio_path: Path | None = None
    try:
        if status_callback:
            status_callback("downloading_audio")
        audio_path = download_audio(video_id, AUDIO_CACHE_DIR)

        if status_callback:
            status_callback("transcribing")
        result = transcribe_audio(audio_path, model_name)

        if status_callback:
            status_callback("whisper_complete")
        return result
    except Exception as exc:
        logger.error("Whisper failed for %s: %s", video_id, exc, exc_info=True)
        if status_callback:
            status_callback("whisper_failed")
        return None
    finally:
        if audio_path is not None and audio_path.exists():
            audio_path.unlink()
