"""Fetch video list and transcripts from YouTube channels/playlists."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from youtube_transcript_api import YouTubeTranscriptApi


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


def get_video_list(channel_or_playlist_url: str) -> list[VideoInfo]:
    """
    Extract list of videos from a YouTube channel or playlist URL.
    Uses yt-dlp to get metadata without downloading videos.
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        channel_or_playlist_url,
    ]

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


def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
    """
    Fetch the transcript for a single video.
    Returns the full transcript as a single string, or None if unavailable.
    """
    if languages is None:
        languages = ["en"]

    try:
        transcript_parts = YouTubeTranscriptApi.get_transcript(video_id, languages=languages)
        return " ".join(part["text"] for part in transcript_parts)
    except Exception:
        return None


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
        video.transcript = fetch_transcript(video.video_id, languages=languages)
        if progress_callback:
            progress_callback(i + 1, len(videos), video)

    return videos
