"""LLM-powered transcript filtering by free-text topic."""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

from .storage import load_index, load_transcript

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
MAX_TRANSCRIPT_CHARS = 12_000
REQUEST_DELAY_SECONDS = 4.0
CACHE_FILENAME = "_filter_cache.json"


@dataclass
class FilterResult:
    """Scored relevance result for a single video."""

    video_id: str
    title: str
    url: str
    relevance_score: int
    explanation: str


def filter_by_topic(
    output_dir: str | Path,
    topic: str,
    threshold: int = 5,
) -> Generator[dict[str, Any], None, None]:
    """Score transcripts against a topic using Gemini and stream progress events."""
    if not topic.strip():
        raise ValueError("Topic must be a non-empty string.")
    if not 0 <= threshold <= 10:
        raise ValueError("Threshold must be in the range 0-10.")

    _configure_gemini()
    model = genai.GenerativeModel(GEMINI_MODEL)

    output_path = Path(output_dir)
    cache = _load_cache(output_path)

    index = load_index(output_path)
    videos_with_transcripts = [entry for entry in index if entry.get("has_transcript")]
    total = len(videos_with_transcripts)
    relevant_count = 0
    has_non_cached_request = False

    yield {"event": "filter_start", "total": total, "topic": topic}

    for current, entry in enumerate(videos_with_transcripts, start=1):
        video_id = str(entry["video_id"])
        title = str(entry.get("title", "Unknown"))
        url = str(entry.get("url", f"https://www.youtube.com/watch?v={video_id}"))
        cache_key = _cache_key(video_id, topic)

        try:
            cached_value = cache.get(cache_key)
            if isinstance(cached_value, dict):
                score = int(cached_value["relevance_score"])
                explanation = str(cached_value.get("explanation", ""))
                logger.info("Topic filter cache hit for video_id=%s", video_id)
            else:
                if has_non_cached_request:
                    time.sleep(REQUEST_DELAY_SECONDS)

                transcript_text = load_transcript(output_path, str(entry["file"]))
                score, explanation = _score_transcript(transcript_text, topic, model)
                has_non_cached_request = True

                cache[cache_key] = {
                    "relevance_score": score,
                    "explanation": explanation,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                }
                _save_cache(output_path, cache)
        except (
            KeyError,
            TypeError,
            ValueError,
            OSError,
            RuntimeError,
            google_exceptions.GoogleAPIError,
        ) as exc:
            logger.error("Failed to score transcript for %s: %s", video_id, exc, exc_info=True)
            score = -1
            explanation = f"Scoring failed: {exc}"

        result = FilterResult(
            video_id=video_id,
            title=title,
            url=url,
            relevance_score=score,
            explanation=explanation,
        )
        is_relevant = result.relevance_score >= threshold
        if is_relevant:
            relevant_count += 1

        yield {
            "event": "filter_progress",
            "current": current,
            "total": total,
            "video_id": result.video_id,
            "title": result.title,
            "url": result.url,
            "relevance_score": result.relevance_score,
            "explanation": result.explanation,
            "relevant": is_relevant,
        }

    yield {
        "event": "filter_done",
        "total": total,
        "relevant_count": relevant_count,
        "topic": topic,
    }


def _load_cache(output_dir: Path) -> dict[str, dict[str, Any]]:
    """Load the topic-filter cache from disk."""
    cache_path = output_dir / CACHE_FILENAME
    if not cache_path.exists():
        return {}

    try:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read filter cache at %s: %s", cache_path, exc)
        return {}

    if not isinstance(payload, dict):
        logger.warning("Ignoring invalid cache format at %s: expected JSON object", cache_path)
        return {}
    return payload


def _save_cache(output_dir: Path, cache: dict[str, dict[str, Any]]) -> None:
    """Persist the topic-filter cache to disk."""
    cache_path = output_dir / CACHE_FILENAME
    cache_path.write_text(
        json.dumps(cache, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def _cache_key(video_id: str, topic: str) -> str:
    """Build a normalized cache key for (video_id, topic)."""
    return f"{video_id}:{topic.strip().lower()}"


def _configure_gemini() -> None:
    """Configure the Gemini client from environment variables."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    genai.configure(api_key=api_key)


def _score_transcript(
    transcript_text: str,
    topic: str,
    model: genai.GenerativeModel,
) -> tuple[int, str]:
    """Send transcript text to Gemini and return (relevance_score, explanation)."""
    truncated = transcript_text[:MAX_TRANSCRIPT_CHARS]

    prompt = (
        "You are a content relevance judge. Given a YouTube video transcript and a topic "
        "of interest, rate how relevant the video is to the topic.\n\n"
        f"Topic: {topic}\n\n"
        "Transcript (may be truncated):\n"
        f"{truncated}\n\n"
        "Respond with ONLY a JSON object, no markdown fences:\n"
        '{"relevance_score": <integer 0-10>, "explanation": "<1-2 sentence explanation>"}\n\n'
        "Scoring guide:\n"
        "- 0-2: Not relevant at all\n"
        "- 3-4: Tangentially related\n"
        "- 5-6: Somewhat relevant, touches on the topic\n"
        "- 7-8: Clearly relevant, discusses the topic substantially\n"
        "- 9-10: Highly relevant, the topic is a main focus"
    )

    response = model.generate_content(prompt)
    response_text = getattr(response, "text", "")
    if not isinstance(response_text, str) or not response_text.strip():
        raise ValueError("Gemini returned an empty response.")

    parsed = _parse_response_json(response_text)

    try:
        raw_score = int(parsed["relevance_score"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid relevance_score in Gemini response: {parsed}") from exc

    explanation = str(parsed.get("explanation", "")).strip()
    score = max(0, min(10, raw_score))
    return score, explanation


def _parse_response_json(response_text: str) -> dict[str, Any]:
    """Parse a Gemini response body containing JSON (possibly fenced)."""
    cleaned = response_text.strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
    cleaned = re.sub(r"^\s*json\s*", "", cleaned, flags=re.IGNORECASE)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Gemini response did not include JSON: {response_text!r}")

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Gemini JSON response: {response_text!r}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Gemini response JSON must be an object: {response_text!r}")
    return parsed
