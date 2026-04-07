"""Service layer providing generator-based transcript fetching with progress."""

from __future__ import annotations

import json
import logging
import subprocess
import time
from collections.abc import Generator
from pathlib import Path

from .fetcher import TranscriptThrottledError, fetch_transcript, get_video_list
from .storage import extract_transcript_body, load_index, save_transcripts

logger = logging.getLogger(__name__)


def fetch_channel_transcripts(
    url: str,
    lang: str = "en",
    limit: int | None = None,
) -> Generator[dict, None, None]:
    """Fetch transcripts for all videos in a channel/playlist, yielding progress.

    Args:
        url: YouTube channel or playlist URL.
        lang: Language code for YouTube captions.
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
    output_dir = "./transcripts"
    cached_entries: dict[str, dict] = {}
    original_index: list[dict] = []

    try:
        original_index = load_index(output_dir)
        cached_entries = {
            entry["video_id"]: entry
            for entry in original_index
            if entry.get("has_transcript") and isinstance(entry.get("video_id"), str)
        }
    except FileNotFoundError:
        logger.debug("No index found at %s; all videos will be fetched", output_dir)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load transcript index from %s: %s", output_dir, exc)

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

    last_was_api_call = False

    for i, video in enumerate(videos):
        transcript_source: str | None = None
        cached_entry = cached_entries.get(video.video_id)

        if cached_entry and isinstance(cached_entry.get("file"), str):
            body = extract_transcript_body(output_dir, cached_entry["file"])
            if body is not None:
                yield {"event": "video_status", "video_id": video.video_id, "step": "cached"}
                video.transcript = body
                transcript_source = "cached"
                last_was_api_call = False
            else:
                cached_entry = None

        if cached_entry is None:
            if last_was_api_call:
                time.sleep(1.5)

            # Step 1: Check YouTube captions
            yield {"event": "video_status", "video_id": video.video_id, "step": "checking_captions"}

            try:
                text = fetch_transcript(video.video_id, languages=[lang])
            except TranscriptThrottledError:
                yield {
                    "event": "video_status",
                    "video_id": video.video_id,
                    "step": "skipped",
                    "skip_reason": "throttled",
                }
                video.transcript = None
                yield {
                    "event": "progress",
                    "current": i + 1,
                    "total": total,
                    "video_id": video.video_id,
                    "title": video.title,
                    "duration": video.duration,
                    "upload_date": video.upload_date,
                    "url": video.url,
                    "has_transcript": False,
                    "transcript_source": None,
                }
                last_was_api_call = True
                break

            if text is not None:
                yield {"event": "video_status", "video_id": video.video_id, "step": "captions_found"}
                video.transcript = text
                transcript_source = "youtube"
            else:
                yield {"event": "video_status", "video_id": video.video_id, "step": "no_captions"}
                yield {
                    "event": "video_status",
                    "video_id": video.video_id,
                    "step": "skipped",
                    "skip_reason": "no_captions",
                }
                video.transcript = None

            last_was_api_call = True

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
        save_transcripts(videos, output_dir)

        current_ids = {v.video_id for v in videos}
        extra_entries = [
            entry
            for entry in original_index
            if isinstance(entry.get("video_id"), str) and entry["video_id"] not in current_ids
        ]
        if extra_entries:
            try:
                new_index = load_index(output_dir)
                new_index.extend(extra_entries)
                index_path = Path(output_dir) / "_index.json"
                index_path.write_text(
                    json.dumps(new_index, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
            except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
                logger.warning("Failed to merge previous index entries: %s", exc)

    yield {
        "event": "done",
        "total": total,
        "with_transcript": sum(1 for v in videos if v.transcript),
        "output_dir": output_dir,
    }
