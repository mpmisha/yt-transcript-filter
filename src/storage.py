"""Save and load transcripts to/from disk."""

from __future__ import annotations

import json
from pathlib import Path

from .fetcher import VideoInfo


def sanitize_filename(name: str) -> str:
    """Remove characters that are invalid in filenames."""
    invalid_chars = '<>:"/\\|?*'
    for ch in invalid_chars:
        name = name.replace(ch, "_")
    return name.strip()[:200]  # cap length


def _format_duration(seconds: int | float | None) -> str:
    """Format duration in seconds as M:SS."""
    if seconds is None:
        return "Unknown"
    total = int(seconds)
    m = total // 60
    s = total % 60
    return f"{m}:{s:02d}"


def _format_upload_date(date_str: str | None) -> str:
    """Format YYYYMMDD as YYYY-MM-DD."""
    if not date_str:
        return "Unknown"
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def format_transcript_as_markdown(video: VideoInfo) -> str:
    """Format a transcript as a Markdown document with title, metadata, and paragraphs.

    Speaker changes marked by '>>' in the raw transcript are used as paragraph breaks.
    """
    lines = [
        f"# {video.title}",
        "",
        f"**Video:** https://www.youtube.com/watch?v={video.video_id}",
        f"**Video ID:** {video.video_id}",
        f"**Upload Date:** {_format_upload_date(video.upload_date)}",
        f"**Duration:** {_format_duration(video.duration)}",
        "",
        "---",
        "",
    ]

    if video.transcript:
        paragraphs = video.transcript.split(">>")
        for paragraph in paragraphs:
            text = paragraph.strip()
            if text:
                lines.append(text)
                lines.append("")

    return "\n".join(lines)


def save_transcripts(videos: list[VideoInfo], output_dir: str | Path) -> Path:
    """
    Save transcripts to a directory, one .md file per video.
    Also saves a metadata index as JSON.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    index = []

    for video in videos:
        safe_name = sanitize_filename(video.title)
        filename = f"{safe_name}__{video.video_id}.md"
        filepath = output_dir / filename

        content = format_transcript_as_markdown(video)
        filepath.write_text(content, encoding="utf-8")

        index.append({
            "video_id": video.video_id,
            "title": video.title,
            "url": video.url,
            "duration": video.duration,
            "upload_date": video.upload_date,
            "has_transcript": video.transcript is not None,
            "file": filename,
        })

    index_path = output_dir / "_index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")

    return output_dir


def load_index(output_dir: str | Path) -> list[dict]:
    """Load the metadata index from a previously saved transcript directory."""
    index_path = Path(output_dir) / "_index.json"
    if not index_path.exists():
        raise FileNotFoundError(f"No index found at {index_path}")
    return json.loads(index_path.read_text(encoding="utf-8"))


def load_transcript(output_dir: str | Path, filename: str) -> str:
    """Load a single transcript file."""
    filepath = Path(output_dir) / filename
    return filepath.read_text(encoding="utf-8")


def extract_transcript_body(output_dir: str | Path, filename: str) -> str | None:
    """Extract transcript body from a saved markdown transcript file."""
    filepath = Path(output_dir) / filename
    if not filepath.exists():
        return None

    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError:
        return None

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return None

    body = parts[1].strip()
    return body if body else None
