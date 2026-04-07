# BE Developer — LLM Topic Filter Module

## Goal

Create `src/llm_filter.py` — a module that uses Google Gemini to score transcript relevance against a user-provided topic. Exposes a generator function that streams progress events (same pattern as `fetch_channel_transcripts` in `service.py`).

## Files

| Action | File |
|--------|------|
| **Create** | `src/llm_filter.py` |
| **Modify** | `requirements.txt` |

## Blocked By

Nothing — can start immediately.

## Delivers

A `filter_by_topic()` generator that reads transcripts from disk, scores each with Gemini, caches results, and yields SSE-compatible progress dicts.

---

## Detailed Steps

### 1. Add dependency to `requirements.txt`

Add:
```
google-generativeai>=0.8.0
```

### 2. Create `src/llm_filter.py`

#### 2a. Imports and constants

```python
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import google.generativeai as genai

from .storage import load_index, load_transcript

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
MAX_TRANSCRIPT_CHARS = 12_000
REQUEST_DELAY_SECONDS = 4.0
CACHE_FILENAME = "_filter_cache.json"
```

- `MAX_TRANSCRIPT_CHARS` — truncate transcripts to ~3,000 tokens to stay within free tier
- `REQUEST_DELAY_SECONDS` — 4s between calls → 15 req/min limit is safely respected
- `CACHE_FILENAME` — stored alongside transcripts in the output directory

#### 2b. FilterResult dataclass

```python
@dataclass
class FilterResult:
    video_id: str
    title: str
    url: str
    relevance_score: int
    explanation: str
```

#### 2c. Cache helpers

```python
def _load_cache(output_dir: Path) -> dict:
    cache_path = output_dir / CACHE_FILENAME
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt filter cache, starting fresh")
    return {}


def _save_cache(output_dir: Path, cache: dict) -> None:
    cache_path = output_dir / CACHE_FILENAME
    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def _cache_key(video_id: str, topic: str) -> str:
    return f"{video_id}:{topic.strip().lower()}"
```

#### 2d. Gemini scoring function

```python
def _configure_gemini() -> None:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY environment variable is not set. "
            "Get a free key at https://aistudio.google.com/apikey"
        )
    genai.configure(api_key=api_key)


def _score_transcript(transcript_text: str, topic: str, model: genai.GenerativeModel) -> tuple[int, str]:
    """Send transcript to Gemini and return (score, explanation)."""
    truncated = transcript_text[:MAX_TRANSCRIPT_CHARS]

    prompt = f"""You are a content relevance judge. Given a YouTube video transcript and a topic of interest, rate how relevant the video is to the topic.

Topic: {topic}

Transcript (may be truncated):
{truncated}

Respond with ONLY a JSON object, no markdown fences:
{{"relevance_score": <integer 0-10>, "explanation": "<1-2 sentence explanation>"}}

Scoring guide:
- 0-2: Not relevant at all
- 3-4: Tangentially related
- 5-6: Somewhat relevant, touches on the topic
- 7-8: Clearly relevant, discusses the topic substantially
- 9-10: Highly relevant, the topic is a main focus"""

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
    if text.endswith("```"):
        text = text[:-3].strip()
    if text.startswith("json"):
        text = text[4:].strip()

    parsed = json.loads(text)
    score = max(0, min(10, int(parsed["relevance_score"])))
    explanation = str(parsed.get("explanation", ""))
    return score, explanation
```

Key details:
- Truncate to 12,000 chars to keep token usage low
- Strip markdown fences — Gemini sometimes wraps JSON in ```json blocks
- Clamp score to 0-10 range
- Parse as JSON with error handling in the caller

#### 2e. Main generator: `filter_by_topic()`

```python
def filter_by_topic(
    output_dir: str | Path,
    topic: str,
    threshold: int = 5,
) -> Generator[dict, None, None]:
    """Score all transcripts against a topic using Gemini.

    Yields SSE-compatible dicts: filter_start, filter_progress, filter_done, filter_error.
    Results are cached per (video_id, topic) to avoid redundant API calls.
    """
    output_dir = Path(output_dir)

    _configure_gemini()
    model = genai.GenerativeModel(GEMINI_MODEL)

    index = load_index(output_dir)
    videos_with_transcripts = [e for e in index if e.get("has_transcript")]
    total = len(videos_with_transcripts)

    yield {
        "event": "filter_start",
        "total": total,
        "topic": topic,
    }

    cache = _load_cache(output_dir)
    relevant_count = 0

    for i, entry in enumerate(videos_with_transcripts):
        video_id = entry["video_id"]
        title = entry["title"]
        url = entry.get("url", f"https://www.youtube.com/watch?v={video_id}")
        key = _cache_key(video_id, topic)

        try:
            if key in cache:
                score = cache[key]["relevance_score"]
                explanation = cache[key]["explanation"]
                logger.info("Cache hit for %s", video_id)
            else:
                transcript_text = load_transcript(output_dir, entry["file"])
                score, explanation = _score_transcript(transcript_text, topic, model)

                cache[key] = {
                    "relevance_score": score,
                    "explanation": explanation,
                    "cached_at": datetime.now(timezone.utc).isoformat(),
                }
                _save_cache(output_dir, cache)

                # Rate limit: wait between Gemini calls (not needed for cache hits)
                if i < total - 1:
                    time.sleep(REQUEST_DELAY_SECONDS)

        except Exception as exc:
            logger.error("Gemini scoring failed for %s: %s", video_id, exc, exc_info=True)
            score = -1
            explanation = f"Scoring failed: {exc}"

        is_relevant = score >= threshold

        if is_relevant:
            relevant_count += 1

        yield {
            "event": "filter_progress",
            "current": i + 1,
            "total": total,
            "video_id": video_id,
            "title": title,
            "url": url,
            "relevance_score": score,
            "explanation": explanation,
            "relevant": is_relevant,
        }

    yield {
        "event": "filter_done",
        "total": total,
        "relevant_count": relevant_count,
        "topic": topic,
    }
```

Key behaviors:
- Loads all transcripts with `has_transcript: true` from the index
- Checks cache before calling Gemini — cache hits skip the API call and rate limit delay
- Saves cache after each successful scoring (crash-safe)
- On error per video: yields score=-1 with error explanation (doesn't abort the whole run)
- Rate limits at 4s between Gemini calls (15 req/min)

---

## Expected Final State

### File: `src/llm_filter.py`

The complete module with:
- `FilterResult` dataclass
- `_load_cache()` / `_save_cache()` / `_cache_key()` — JSON-file cache helpers
- `_configure_gemini()` — reads `GEMINI_API_KEY` env var
- `_score_transcript()` — sends prompt to Gemini, parses JSON response
- `filter_by_topic()` — public generator, yields `filter_start`, `filter_progress`, `filter_done` events

### File: `requirements.txt`

```
yt-dlp>=2024.0.0
youtube-transcript-api>=0.6.0
click>=8.0.0
rich>=13.0.0
google-generativeai>=0.8.0
```

---

## Verification

1. `python3 -c "from src.llm_filter import filter_by_topic; print('OK')"` — no import errors
2. `grep google-generativeai requirements.txt` — dependency present
3. With `GEMINI_API_KEY` set, run a quick integration test:
   ```python
   import os
   os.environ["GEMINI_API_KEY"] = "your-key"
   from src.llm_filter import filter_by_topic
   for event in filter_by_topic("./transcripts", "app monetization"):
       print(event)
   ```
4. Run the same filter again — should see "Cache hit" in logs (no Gemini calls)
