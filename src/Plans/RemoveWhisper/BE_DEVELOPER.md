# BE Developer — Remove Whisper from Backend

## Goal

Delete the Whisper transcription module entirely, remove the fallback function from `fetcher.py`, and simplify the service pipeline in `service.py` to only use YouTube captions. Also clean up dependencies and gitignore.

## Files

| Action | File |
|--------|------|
| **Delete** | `src/whisper_transcriber.py` |
| **Modify** | `src/fetcher.py` |
| **Modify** | `src/service.py` |
| **Modify** | `requirements.txt` |
| **Modify** | `.gitignore` |

## Blocked By

Nothing — can start immediately.

## Delivers

A simplified service pipeline that only fetches YouTube captions (no Whisper fallback). The `fetch_channel_transcripts()` generator no longer accepts a `whisper_model` parameter and no longer emits Whisper-related status events.

---

## Detailed Steps

### 1. Delete `src/whisper_transcriber.py`

Delete the entire file. It contains:
- `download_audio()` — yt-dlp audio download
- `transcribe_audio()` — faster-whisper transcription
- `whisper_transcript()` — combined download + transcribe
- `_get_model()` — model caching
- `VALID_MODELS`, `AUDIO_CACHE_DIR` constants

All of this is no longer needed.

### 2. Modify `src/fetcher.py` — Remove `fetch_transcript_with_fallback()`

Remove the entire `fetch_transcript_with_fallback()` function (currently at the bottom of the file). This function:
- Accepts a `whisper_model` parameter
- Imports `whisper_transcript` from `whisper_transcriber`
- Falls back to Whisper when YouTube captions are unavailable

**Remove this entire function:**

```python
def fetch_transcript_with_fallback(
    video_id: str,
    languages: list[str] | None = None,
    whisper_model: str | None = None,
    status_callback: Callable[[str], None] | None = None,
) -> tuple[str | None, str | None]:
    """Fetch transcript with optional Whisper fallback.

    Returns (transcript_text, source) where source is "youtube", "whisper", or None.
    """
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

    if status_callback:
        status_callback("skipped")

    return None, None
```

Also check if the `Callable` import from `collections.abc` is still needed by other functions in the file. If `fetch_transcript_with_fallback` was the only user, remove the import too.

### 3. Modify `src/service.py` — Remove Whisper from the pipeline

The `fetch_channel_transcripts()` generator needs these changes:

#### 3a. Remove `whisper_model` parameter

**Before:**
```python
def fetch_channel_transcripts(
    url: str,
    lang: str = "en",
    whisper_model: str | None = None,
    limit: int | None = None,
) -> Generator[dict, None, None]:
```

**After:**
```python
def fetch_channel_transcripts(
    url: str,
    lang: str = "en",
    limit: int | None = None,
) -> Generator[dict, None, None]:
```

#### 3b. Update the docstring

Remove the `whisper_model` arg from the docstring. Remove reference to Whisper fallback transcription.

#### 3c. Remove `with_whisper_count` variable

Remove:
```python
with_whisper_count = 0
```

And remove:
```python
if transcript_source == "whisper":
    with_whisper_count += 1
```

#### 3d. Replace the Whisper fallback branch

**Remove this entire block** (the `if whisper_model is not None:` branch after `no_captions`):

```python
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
```

**Replace with** just the skipped path (always skip when no captions):
```python
            yield {"event": "video_status", "video_id": video.video_id, "step": "skipped"}
            video.transcript = None
```

#### 3e. Remove `with_whisper` from the done event

**Before:**
```python
    yield {
        "event": "done",
        "total": total,
        "with_transcript": sum(1 for v in videos if v.transcript),
        "with_whisper": with_whisper_count,
        "output_dir": "./transcripts",
    }
```

**After:**
```python
    yield {
        "event": "done",
        "total": total,
        "with_transcript": sum(1 for v in videos if v.transcript),
        "output_dir": "./transcripts",
    }
```

### 4. Modify `requirements.txt` — Remove `faster-whisper`

Remove this line:
```
faster-whisper>=1.0.0
```

### 5. Modify `.gitignore` — Remove `.audio_cache/`

Remove the `.audio_cache/` entry. This directory was only used for temporary audio files during Whisper transcription.

---

## Expected Final State

### `src/service.py` — Simplified pipeline (relevant section)

```python
    for i, video in enumerate(videos):
        transcript_source: str | None = None

        # Check YouTube captions
        yield {"event": "video_status", "video_id": video.video_id, "step": "checking_captions"}

        text = fetch_transcript(video.video_id, languages=[lang])

        if text is not None:
            yield {"event": "video_status", "video_id": video.video_id, "step": "captions_found"}
            video.transcript = text
            transcript_source = "youtube"
        else:
            yield {"event": "video_status", "video_id": video.video_id, "step": "no_captions"}
            yield {"event": "video_status", "video_id": video.video_id, "step": "skipped"}
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
            "has_transcript": video.transcript is not None,
            "transcript_source": transcript_source,
        }

        if i < total - 1:
            time.sleep(1.5)
```

---

## Verification

1. `python3 -c "from src.service import fetch_channel_transcripts; print('OK')"` — no import errors
2. `python3 -c "from src.fetcher import fetch_transcript; print('OK')"` — no import errors
3. `grep -ri whisper src/` — returns nothing
4. `grep faster-whisper requirements.txt` — returns nothing
5. Verify `src/whisper_transcriber.py` no longer exists
