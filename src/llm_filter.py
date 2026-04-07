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

GEMINI_MODEL = "gemini-2.5-flash-lite"
MAX_TRANSCRIPT_CHARS = 12_000
BATCH_SIZE = 10
REQUEST_DELAY_SECONDS = 4.0
MAX_RETRIES = 3
RETRY_BASE_DELAY = 15.0
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
    current = 0

    yield {"event": "filter_start", "total": total, "topic": topic}

    # Separate cached from uncached videos
    cached_videos: list[tuple[int, dict]] = []
    uncached_videos: list[tuple[int, dict]] = []
    for idx, entry in enumerate(videos_with_transcripts):
        cache_key = _cache_key(str(entry["video_id"]), topic)
        cached_value = cache.get(cache_key)
        if isinstance(cached_value, dict):
            cached_videos.append((idx, entry))
        else:
            uncached_videos.append((idx, entry))

    # Emit cached results immediately
    for _idx, entry in cached_videos:
        current += 1
        video_id = str(entry["video_id"])
        cache_key = _cache_key(video_id, topic)
        cached_value = cache[cache_key]
        score = int(cached_value["relevance_score"])
        explanation = str(cached_value.get("explanation", ""))
        is_relevant = score >= threshold
        if is_relevant:
            relevant_count += 1
        logger.info("Topic filter cache hit for video_id=%s", video_id)
        yield _progress_event(entry, score, explanation, is_relevant, current, total)

    # Batch-score uncached videos
    has_previous_batch = False
    for batch_start in range(0, len(uncached_videos), BATCH_SIZE):
        batch = uncached_videos[batch_start : batch_start + BATCH_SIZE]

        if has_previous_batch:
            time.sleep(REQUEST_DELAY_SECONDS)

        # Load transcripts for this batch
        batch_items: list[tuple[dict, str]] = []
        for _idx, entry in batch:
            try:
                transcript_text = load_transcript(output_path, str(entry["file"]))
                batch_items.append((entry, transcript_text))
            except OSError as exc:
                current += 1
                logger.error("Failed to load transcript for %s: %s", entry["video_id"], exc)
                yield _progress_event(entry, -1, f"Scoring failed: {exc}", False, current, total)

        if not batch_items:
            continue

        # Try batch scoring
        batch_scores = _score_transcripts_batch(
            [(str(e["video_id"]), t) for e, t in batch_items],
            topic,
            model,
        )
        has_previous_batch = True

        # Emit results and cache
        for entry, _transcript in batch_items:
            current += 1
            video_id = str(entry["video_id"])

            if video_id in batch_scores:
                score, explanation = batch_scores[video_id]
            else:
                score, explanation = -1, "Missing from batch response"

            cache_key = _cache_key(video_id, topic)
            cache[cache_key] = {
                "relevance_score": score,
                "explanation": explanation,
                "cached_at": datetime.now(timezone.utc).isoformat(),
            }

            is_relevant = score >= threshold
            if is_relevant:
                relevant_count += 1
            yield _progress_event(entry, score, explanation, is_relevant, current, total)

        _save_cache(output_path, cache)

    yield {
        "event": "filter_done",
        "total": total,
        "relevant_count": relevant_count,
        "topic": topic,
    }


def _progress_event(
    entry: dict,
    score: int,
    explanation: str,
    is_relevant: bool,
    current: int,
    total: int,
) -> dict[str, Any]:
    """Build a filter_progress SSE event dict."""
    video_id = str(entry["video_id"])
    return {
        "event": "filter_progress",
        "current": current,
        "total": total,
        "video_id": video_id,
        "title": str(entry.get("title", "Unknown")),
        "url": str(entry.get("url", f"https://www.youtube.com/watch?v={video_id}")),
        "relevance_score": score,
        "explanation": explanation,
        "relevant": is_relevant,
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


def _generate_with_retry(
    model: genai.GenerativeModel,
    prompt: str,
) -> str:
    """Call Gemini with exponential backoff on 429 rate-limit errors."""
    for attempt in range(MAX_RETRIES):
        try:
            response = model.generate_content(prompt)
            text = getattr(response, "text", "")
            return text if isinstance(text, str) else ""
        except google_exceptions.ResourceExhausted as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            delay = RETRY_BASE_DELAY * (2 ** attempt)
            logger.warning(
                "Rate limited (attempt %d/%d), retrying in %.0fs: %s",
                attempt + 1, MAX_RETRIES, delay, exc,
            )
            time.sleep(delay)
    return ""


def _score_transcripts_batch(
    items: list[tuple[str, str]],
    topic: str,
    model: genai.GenerativeModel,
) -> dict[str, tuple[int, str]]:
    """Score multiple transcripts in a single Gemini call.

    Args:
        items: List of (video_id, transcript_text) tuples.
        topic: The topic to score against.
        model: Configured Gemini model.

    Returns:
        Dict mapping video_id to (score, explanation). Videos missing from
        the response or with parse errors get score -1.
    """
    transcript_sections = []
    for video_id, transcript_text in items:
        truncated = transcript_text[:MAX_TRANSCRIPT_CHARS]
        transcript_sections.append(f"=== VIDEO: {video_id} ===\n{truncated}")

    all_transcripts = "\n\n".join(transcript_sections)
    video_ids_hint = ", ".join(f'"{vid}"' for vid, _ in items)

    prompt = (
        "You are a content relevance judge. Score each YouTube video transcript "
        "below against the given topic.\n\n"
        f"Topic: {topic}\n\n"
        "Scoring guide:\n"
        "- 0-2: Not relevant at all\n"
        "- 3-4: Tangentially related\n"
        "- 5-6: Somewhat relevant, touches on the topic\n"
        "- 7-8: Clearly relevant, discusses the topic substantially\n"
        "- 9-10: Highly relevant, the topic is a main focus\n\n"
        f"{all_transcripts}\n\n"
        "Respond with ONLY a JSON array, no markdown fences. "
        f"Include exactly one entry per video ID ({video_ids_hint}):\n"
        '[{"video_id": "...", "relevance_score": <integer 0-10>, '
        '"explanation": "<1-2 sentence explanation>"}, ...]'
    )

    try:
        response_text = _generate_with_retry(model, prompt)
        if not response_text.strip():
            raise ValueError("Gemini returned an empty response.")
        parsed_array = _parse_response_json_array(response_text)
    except (ValueError, google_exceptions.GoogleAPIError) as exc:
        logger.warning("Batch scoring failed, falling back to individual: %s", exc)
        return _fallback_individual_scoring(items, topic, model)

    results: dict[str, tuple[int, str]] = {}
    for item in parsed_array:
        try:
            vid = str(item["video_id"])
            raw_score = int(item["relevance_score"])
            explanation = str(item.get("explanation", "")).strip()
            results[vid] = (max(0, min(10, raw_score)), explanation)
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Failed to parse batch item %s: %s", item, exc)

    return results


def _fallback_individual_scoring(
    items: list[tuple[str, str]],
    topic: str,
    model: genai.GenerativeModel,
) -> dict[str, tuple[int, str]]:
    """Score transcripts one-by-one as a fallback when batch scoring fails."""
    results: dict[str, tuple[int, str]] = {}
    for i, (video_id, transcript_text) in enumerate(items):
        if i > 0:
            time.sleep(REQUEST_DELAY_SECONDS)
        try:
            score, explanation = _score_transcript(transcript_text, topic, model)
            results[video_id] = (score, explanation)
        except (
            ValueError,
            RuntimeError,
            google_exceptions.GoogleAPIError,
        ) as exc:
            logger.error("Individual fallback failed for %s: %s", video_id, exc)
            results[video_id] = (-1, f"Scoring failed: {exc}")
    return results


def _parse_response_json_array(response_text: str) -> list[dict[str, Any]]:
    """Parse a Gemini response expecting a JSON array."""
    cleaned = response_text.strip()
    cleaned = re.sub(r"^\s*```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\[.*\]", cleaned, flags=re.DOTALL)
    if match is None:
        raise ValueError(f"Gemini response did not include a JSON array: {response_text[:200]!r}")

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse Gemini JSON array: {response_text[:200]!r}") from exc

    if not isinstance(parsed, list):
        raise ValueError(f"Expected JSON array, got {type(parsed).__name__}")
    return parsed


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

    response_text = _generate_with_retry(model, prompt)
    if not response_text.strip():
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
