"""Service layer providing generator-based transcript fetching with progress."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Generator

from .fetcher import fetch_transcript, get_video_list
from .storage import save_transcripts

logger = logging.getLogger(__name__)


def fetch_channel_transcripts(
    url: str,
    lang: str = "en",
    whisper_model: str | None = None,
    limit: int | None = None,
) -> Generator[dict, None, None]:
    """Fetch transcripts for all videos in a channel/playlist, yielding progress.

    Args:
        url: YouTube channel or playlist URL.
        lang: Language code for YouTube captions.
        whisper_model: Optional Whisper model name for fallback transcription.
        limit: Optional max number of videos to process. None means all.

    Yields ``video_list``, ``video_status``, ``progress``, and ``done`` dicts.

    Raises:
        ValueError: If the URL is invalid or yt-dlp fails to fetch the video list.
    """
    try:
        videos = get_video_list(url)
    except subprocess.CalledProcessError:
        raise ValueError(f"Failed to fetch video list from URL: {url}")

    if limit is not None:
        videos = videos[:limit]

    total = len(videos)

    # Emit video_list event with all video metadata
    yield {
        "event": "video_list",
        "total": total,
        "videos": [
            {
                "video_id": v.video_id,
                "title": v.title,
                "duration": v.duration,
                "upload_date": v.upload_date,
                "url": v.url,
            }
            for v in videos
        ],
    }

    with_whisper_count = 0
    for i, video in enumerate(videos):
        transcript_source: str | None = None

        # Step 1: Check YouTube captions
        yield {"event": "video_status", "video_id": video.video_id, "step": "checking_captions"}

        text = fetch_transcript(video.video_id, languages=[lang])

        if text is not None:
            yield {"event": "video_status", "video_id": video.video_id, "step": "captions_found"}
            video.transcript = text
            transcript_source = "youtube"
        else:
            yield {"event": "video_status", "video_id": video.video_id, "step": "no_captions"}

            if whisper_model is not None:
                from .whisper_transcriber import download_audio, transcribe_audio, AUDIO_CACHE_DIR

                yield {"event": "video_status", "video_id": video.video_id, "step": "downloading_audio"}
                audio_path = None
                try:
                    audio_path = download_audio(video.video_id, AUDIO_CACHE_DIR)
                    yield {"event": "video_status", "video_id": video.video_id, "step": "transcribing"}
                    video.transcript = transcribe_audio(audio_path, whisper_model)
                    transcript_source = "whisper"
                    yield {"event": "video_status", "video_id": video.video_id, "step": "whisper_complete"}
                except Exception as exc:
                    logger.error("Whisper failed for %s: %s", video.video_id, exc, exc_info=True)
                    video.transcript = None
                    yield {
                        "event": "video_status",
                        "video_id": video.video_id,
                        "step": "whisper_failed",
                        "error": str(exc),
                    }
                finally:
                    if audio_path is not None and audio_path.exists():
                        audio_path.unlink()
            else:
                yield {"event": "video_status", "video_id": video.video_id, "step": "skipped"}
                video.transcript = None

        if transcript_source == "whisper":
            with_whisper_count += 1

        yield {
            "event": "progress",
            "current": i + 1,
            "total": total,
            "video_id": video.video_id,
            "title": video.title,
            "duration": video.duration,
            "upload_date": video.upload_date,
            "url": video.url,
            "has_transcript": video.transcript is not None,
            "transcript_source": transcript_source,
        }

    if videos:
        save_transcripts(videos, "./transcripts")

    yield {
        "event": "done",
        "total": total,
        "with_transcript": sum(1 for v in videos if v.transcript),
        "with_whisper": with_whisper_count,
        "output_dir": "./transcripts",
    }
