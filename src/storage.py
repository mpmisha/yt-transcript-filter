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


def save_transcripts(videos: list[VideoInfo], output_dir: str | Path) -> Path:
    """
    Save transcripts to a directory, one .txt file per video.
    Also saves a metadata index as JSON.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    index = []

    for video in videos:
        safe_name = sanitize_filename(video.title)
        filename = f"{safe_name}__{video.video_id}.txt"
        filepath = output_dir / filename

        if video.transcript:
            filepath.write_text(video.transcript, encoding="utf-8")
        else:
            filepath.write_text("[No transcript available]", encoding="utf-8")

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
