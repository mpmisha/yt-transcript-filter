"""Fetch video list and transcripts from YouTube channels/playlists."""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

logger = logging.getLogger(__name__)



@dataclass
class VideoInfo:
    """Metadata for a single YouTube video."""
    video_id: str
    title: str
    url: str
    duration: int | None = None  # seconds
    upload_date: str | None = None
    description: str = ""
    transcript: str | None = None


def _is_single_video_url(url: str) -> bool:
    """Return True if the URL points to a single YouTube video."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    if hostname in ("youtu.be", "www.youtu.be"):
        return True

    if hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch" and "v" in parse_qs(parsed.query):
            return True
        if re.match(r"^/shorts/[\w-]+$", parsed.path):
            return True

    return False


def get_video_list(channel_or_playlist_url: str) -> list[VideoInfo]:
    """
    Extract list of videos from a YouTube channel or playlist URL.
    Uses yt-dlp to get metadata without downloading videos.
    """
    # Resolve yt-dlp from the same virtualenv as the running Python
    yt_dlp_bin = str(Path(sys.executable).parent / "yt-dlp")

    cmd = [
        yt_dlp_bin,
        "--dump-json",
        "--no-warnings",
    ]
    if _is_single_video_url(channel_or_playlist_url):
        cmd.append("--no-playlist")
    else:
        cmd.append("--flat-playlist")
    cmd.append(channel_or_playlist_url)

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        data = json.loads(line)
        video_id = data.get("id", "")
        videos.append(VideoInfo(
            video_id=video_id,
            title=data.get("title", "Unknown"),
            url=data.get("url", f"https://www.youtube.com/watch?v={video_id}"),
            duration=data.get("duration"),
            upload_date=data.get("upload_date"),
            description=data.get("description", ""),
        ))

    return videos


def fetch_transcript(
    video_id: str,
    languages: list[str] | None = None,
) -> tuple[str | None, str | None]:
    """
    Fetch the transcript for a single video.
    Returns a tuple of transcript text and skip reason.
    """
    if languages is None:
        languages = ["en"]

    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=languages)
        return " ".join(snippet.text for snippet in transcript), None
    except NoTranscriptFound:
        logger.debug("No transcript for %s: NoTranscriptFound", video_id)
        return None, "No transcript available"
    except TranscriptsDisabled:
        logger.debug("No transcript for %s: TranscriptsDisabled", video_id)
        return None, "Transcripts disabled by uploader"
    except VideoUnavailable:
        logger.debug("No transcript for %s: VideoUnavailable", video_id)
        return None, "Video unavailable"
    except IpBlocked:
        logger.warning("YouTube blocked request for %s: IpBlocked", video_id)
        return None, "YouTube rate limit (IP blocked)"
    except RequestBlocked:
        logger.warning("YouTube blocked request for %s: RequestBlocked", video_id)
        return None, "YouTube rate limit (request blocked)"
    except Exception as exc:
        logger.warning("Failed to fetch transcript for %s: %s", video_id, exc)
        return None, f"Unexpected error: {exc}"


def fetch_all_transcripts(
    videos: list[VideoInfo],
    languages: list[str] | None = None,
    progress_callback=None,
) -> list[VideoInfo]:
    """
    Fetch transcripts for all videos in the list.
    Updates each VideoInfo in-place and returns the list.
    """
    for i, video in enumerate(videos):
        text, _reason = fetch_transcript(video.video_id, languages=languages)
        video.transcript = text
        if progress_callback:
            progress_callback(i + 1, len(videos), video)
        if i < len(videos) - 1:
            time.sleep(1.5)

    return videos
