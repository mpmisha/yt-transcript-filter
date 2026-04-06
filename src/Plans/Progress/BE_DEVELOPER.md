# BE Developer — Detailed Progress Events

## Goal

Add sub-step SSE events to the fetch pipeline so the frontend can show exactly what's happening for each video in real time. Introduce a `video_list` event (emitted once after discovery) and `video_status` events (emitted during processing of each video).

## Files

| Action | File |
|--------|------|
| **Modify** | `src/service.py` — yield `video_list` and `video_status` events |
| **Modify** | `src/fetcher.py` — add `status_callback` to `fetch_transcript_with_fallback()` |
| **Modify** | `src/whisper_transcriber.py` — add `status_callback` to `whisper_transcript()` |

## Blocked By

Nothing — can start immediately.

## Delivers

Updated generator that yields `video_list`, `video_status`, `progress`, and `done` events in the correct order.

---

## Detailed Steps

### 1. Modify `src/whisper_transcriber.py` — add status callback

**Update `whisper_transcript()` signature:**

Current:
```python
def whisper_transcript(video_id: str, model_name: str) -> str | None:
```

New:
```python
from collections.abc import Callable

def whisper_transcript(
    video_id: str,
    model_name: str,
    status_callback: Callable[[str], None] | None = None,
) -> str | None:
```

**Add callback calls inside the function:**

```python
def whisper_transcript(
    video_id: str,
    model_name: str,
    status_callback: Callable[[str], None] | None = None,
) -> str | None:
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
    except Exception:
        if status_callback:
            status_callback("whisper_failed")
        return None
    finally:
        if audio_path is not None and audio_path.exists():
            audio_path.unlink()
```

**Do NOT change** `download_audio()` or `transcribe_audio()` — they stay as-is. The callback is only added to `whisper_transcript()`.

### 2. Modify `src/fetcher.py` — add status callback to fallback function

**Update `fetch_transcript_with_fallback()` signature:**

Current:
```python
def fetch_transcript_with_fallback(
    video_id: str,
    languages: list[str] | None = None,
    whisper_model: str | None = None,
) -> tuple[str | None, str | None]:
```

New:
```python
from collections.abc import Callable

def fetch_transcript_with_fallback(
    video_id: str,
    languages: list[str] | None = None,
    whisper_model: str | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[str | None, str | None]:
```

**Add callback calls:**

```python
def fetch_transcript_with_fallback(
    video_id: str,
    languages: list[str] | None = None,
    whisper_model: str | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[str | None, str | None]:
    if status_callback:
        status_callback("checking_captions")

    text = fetch_transcript(video_id, languages)
    if text is not None:
        if status_callback:
            status_callback("captions_found")
        return text, "youtube"

    if status_callback:
        status_callback("no_captions")

    if whisper_model is not None:
        from .whisper_transcriber import whisper_transcript
        result = whisper_transcript(video_id, whisper_model, status_callback=status_callback)
        if result is not None:
            return result, "whisper"

    if whisper_model is None:
        if status_callback:
            status_callback("skipped")

    return None, None
```

**Note**: When `whisper_model` is not None, the Whisper function itself emits the `downloading_audio`, `transcribing`, `whisper_complete`/`whisper_failed` callbacks. When `whisper_model` is None, we emit `skipped`.

### 3. Modify `src/service.py` — yield new events

#### 3a. Yield `video_list` event after discovery

After `get_video_list()` returns, yield a `video_list` event containing basic metadata for all videos:

```python
videos = get_video_list(url)  # existing line

total = len(videos)

# NEW: yield video_list event
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
```

#### 3b. Yield `video_status` events via callback

Inside the loop, create a callback that yields `video_status` events, and pass it to `fetch_transcript_with_fallback()`.

**The challenge**: You can't `yield` from inside a callback. Instead, use a list to collect status events, then yield them after the callback fires.

**Implementation pattern using a status collector:**

```python
with_whisper_count = 0
for i, video in enumerate(videos):
    status_steps: list[str] = []

    def on_status(step: str) -> None:
        status_steps.append(step)

    video.transcript, transcript_source = fetch_transcript_with_fallback(
        video.video_id,
        languages=[lang],
        whisper_model=whisper_model,
        status_callback=on_status,
    )
```

**Problem**: This collects all steps but only yields them after the video is fully processed — defeating the purpose of real-time updates.

**Better approach**: Use a queue-based pattern with threading, or restructure to yield inline. The simplest approach that works with generators:

**Restructure the service to yield status events inline by breaking up the fallback logic:**

```python
for i, video in enumerate(videos):
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
            yield {"event": "video_status", "video_id": video.video_id, "step": "downloading_audio"}
            from .whisper_transcriber import download_audio, transcribe_audio, AUDIO_CACHE_DIR, VALID_MODELS

            audio_path = None
            try:
                audio_path = download_audio(video.video_id, AUDIO_CACHE_DIR)
                yield {"event": "video_status", "video_id": video.video_id, "step": "transcribing"}
                video.transcript = transcribe_audio(audio_path, whisper_model)
                transcript_source = "whisper"
                yield {"event": "video_status", "video_id": video.video_id, "step": "whisper_complete"}
            except Exception:
                video.transcript = None
                transcript_source = None
                yield {"event": "video_status", "video_id": video.video_id, "step": "whisper_failed"}
            finally:
                if audio_path is not None and audio_path.exists():
                    audio_path.unlink()
        else:
            yield {"event": "video_status", "video_id": video.video_id, "step": "skipped"}
            video.transcript = None
            transcript_source = None

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
```

**Important**: This approach inlines the Whisper logic directly in the generator so we can `yield` between steps. This means we call `download_audio()` and `transcribe_audio()` directly from `service.py` instead of going through `whisper_transcript()`. The `fetch_transcript_with_fallback()` function is still kept for the CLI path, but the service generator handles the web path inline.

**Alternative (simpler if preferred)**: Keep using `fetch_transcript_with_fallback()` with the callback pattern, but accept that all `video_status` events for a single video arrive in a batch just before the `progress` event. This still gives the UI step-by-step info (it knows *what happened*) but not truly real-time updates during download/transcription. The inline approach above gives true real-time status.

**Recommendation**: Use the inline approach in `service.py` for true real-time SSE streaming.

### 4. Update imports in `src/service.py`

Change:
```python
from .fetcher import fetch_transcript_with_fallback, get_video_list
```

To:
```python
from .fetcher import fetch_transcript, get_video_list
```

Since the service now calls `fetch_transcript()` directly and handles the Whisper fallback inline.

---

## Complete Updated `src/service.py`

```python
"""Service layer providing generator-based transcript fetching with progress."""

from __future__ import annotations

import subprocess
from collections.abc import Generator

from .fetcher import fetch_transcript, get_video_list
from .storage import save_transcripts


def fetch_channel_transcripts(url: str, lang: str = "en", whisper_model: str | None = None) -> Generator[dict, None, None]:
    try:
        videos = get_video_list(url)
    except subprocess.CalledProcessError:
        raise ValueError(f"Failed to fetch video list from URL: {url}")

    total = len(videos)

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
                except Exception:
                    video.transcript = None
                    yield {"event": "video_status", "video_id": video.video_id, "step": "whisper_failed"}
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
```

---

## What NOT to Change

- `src/fetcher.py`: Keep `fetch_transcript_with_fallback()` as-is for the CLI path. Only change if you want to add the `status_callback` param (optional, not required for this task since the service handles it inline).
- `src/whisper_transcriber.py`: No changes needed. The service calls `download_audio()` and `transcribe_audio()` directly.
- `web/api.py`: No changes. Already streams all yielded dicts.

---

## Verification

1. **No regression**: Fetch a channel without Whisper → should see `video_list` + `checking_captions` + `captions_found`/`no_captions`/`skipped` + `progress` + `done` events in correct order
2. **Whisper path**: Fetch with Whisper enabled on a channel with no captions → should see `downloading_audio` → `transcribing` → `whisper_complete` steps between `no_captions` and `progress`
3. **Whisper failure**: If audio download fails → should see `whisper_failed` step, video marked `has_transcript: false`
4. **video_list event**: Should contain all video metadata and be emitted before any `video_status` events
5. **Event order**: For each video: `video_status` events → `progress` event. Never a `progress` before its `video_status` events.

## Definition of Done

- [ ] `service.py` yields `video_list` event after `get_video_list()`
- [ ] `service.py` yields `video_status` events inline before each step
- [ ] Steps emitted in real-time (not batched)
- [ ] Whisper download/transcribe steps yield individual `video_status` events
- [ ] Whisper failure yields `whisper_failed` step
- [ ] `progress` event still emitted after each video (backwards compatible)
- [ ] `done` event unchanged
- [ ] Audio files cleaned up in `finally` block
- [ ] No changes required in `web/api.py`
