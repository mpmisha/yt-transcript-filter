# BE Developer — Whisper Fallback Transcription

## Goal

Add a Whisper-based fallback so that when YouTube captions are unavailable, the app downloads the audio and transcribes it locally using `faster-whisper`. The user selects the Whisper model from the UI; when disabled (`None`), behavior is identical to today.

## Files

| Action | File |
|--------|------|
| **Create** | `src/whisper_transcriber.py` — audio download + Whisper transcription |
| **Modify** | `src/fetcher.py` — add `fetch_transcript_with_fallback()` |
| **Modify** | `src/service.py` — accept `whisper_model` param, add `transcript_source` to events |
| **Modify** | `requirements.txt` — add `faster-whisper` |
| **Modify** | `.gitignore` — add `.audio_cache/` |

## Blocked By

Nothing — can start immediately.

## Delivers

Updated `fetch_channel_transcripts(url, lang, whisper_model=None)` generator that:
- Tries YouTube captions first
- Falls back to Whisper when captions unavailable and `whisper_model` is set
- Yields `transcript_source` in every progress event

---

## Detailed Steps

### 1. Add `faster-whisper` to `requirements.txt`

Add this line to the existing `requirements.txt`:
```
faster-whisper>=1.0.0
```

### 2. Create `src/whisper_transcriber.py`

This module handles audio download and Whisper transcription.

#### Constants

```python
VALID_MODELS = ("tiny", "base", "small", "medium")
AUDIO_CACHE_DIR = Path(".audio_cache")
```

#### `download_audio(video_id, output_dir) -> Path`

```python
def download_audio(video_id: str, output_dir: Path) -> Path:
```

- Runs `yt-dlp -x --audio-format mp3 -o "{output_dir}/{video_id}.%(ext)s" "https://www.youtube.com/watch?v={video_id}"`
- Uses `subprocess.run()` with `check=True`
- Returns the path to the downloaded `.mp3` file
- Raises `RuntimeError` if download fails
- **Security**: Build the YouTube URL from `video_id` only — do not pass arbitrary user strings to subprocess

#### `transcribe_audio(audio_path, model_name) -> str`

```python
def transcribe_audio(audio_path: Path, model_name: str) -> str:
```

- Loads the `faster-whisper` model via `_get_model()` (see caching below)
- Calls `model.transcribe(str(audio_path))`
- Iterates segments and joins all `.text` values into a single string
- Returns the full transcript text

#### `whisper_transcript(video_id, model_name) -> str | None`

```python
def whisper_transcript(video_id: str, model_name: str) -> str | None:
```

- Validates `model_name` is in `VALID_MODELS`, raises `ValueError` if not
- Creates `AUDIO_CACHE_DIR` if it doesn't exist
- Calls `download_audio(video_id, AUDIO_CACHE_DIR)`
- Calls `transcribe_audio(audio_path, model_name)`
- **Deletes the audio file** in a `finally` block (cleanup even on failure)
- Returns transcript text, or `None` if any step fails
- Wraps in `try/except` — logs error, returns `None`, never crashes the batch

#### Model Caching

The Whisper model is expensive to load. Cache it at module level:

```python
_cached_model: WhisperModel | None = None
_cached_model_name: str | None = None

def _get_model(model_name: str) -> WhisperModel:
    global _cached_model, _cached_model_name
    if _cached_model is None or _cached_model_name != model_name:
        _cached_model = WhisperModel(model_name)
        _cached_model_name = model_name
    return _cached_model
```

### 3. Modify `src/fetcher.py` — add fallback function

Add a new function. Do NOT modify the existing `fetch_transcript()`.

```python
def fetch_transcript_with_fallback(
    video_id: str,
    languages: list[str] | None = None,
    whisper_model: str | None = None,
) -> tuple[str | None, str | None]:
```

**Flow:**
1. Call existing `fetch_transcript(video_id, languages)`
2. If result is not `None`, return `(result, "youtube")`
3. If result is `None` and `whisper_model` is not `None`:
   - Import `whisper_transcript` from `src.whisper_transcriber`
   - Call `whisper_transcript(video_id, whisper_model)`
   - If result is not `None`, return `(result, "whisper")`
4. Return `(None, None)`

**Return type**: `tuple[str | None, str | None]` — `(transcript_text, source)` where source is `"youtube"`, `"whisper"`, or `None`.

### 4. Modify `src/service.py`

#### Update function signature

**Current:**
```python
def fetch_channel_transcripts(url: str, lang: str = "en") -> Generator[dict, None, None]:
```

**New:**
```python
def fetch_channel_transcripts(url: str, lang: str = "en", whisper_model: str | None = None) -> Generator[dict, None, None]:
```

#### Update the fetch loop

**Current code:**
```python
for i, video in enumerate(videos):
    video.transcript = fetch_transcript(video.video_id, languages=[lang])
```

**Replace with:**
```python
with_whisper_count = 0
for i, video in enumerate(videos):
    video.transcript, transcript_source = fetch_transcript_with_fallback(
        video.video_id, languages=[lang], whisper_model=whisper_model
    )
    if transcript_source == "whisper":
        with_whisper_count += 1
```

#### Update progress event — add `transcript_source`

```python
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

#### Update done event — add `with_whisper`

```python
yield {
    "event": "done",
    "total": total,
    "with_transcript": sum(1 for v in videos if v.transcript),
    "with_whisper": with_whisper_count,
    "output_dir": "./transcripts",
}
```

#### Update import

Change:
```python
from .fetcher import fetch_transcript, get_video_list
```
To:
```python
from .fetcher import fetch_transcript_with_fallback, get_video_list
```

### 5. Add `.audio_cache/` to `.gitignore`

Add this line to the project root `.gitignore`:
```
.audio_cache/
```

---

## Error Handling Summary

| Scenario | Behavior |
|----------|----------|
| YouTube captions available | Use them, `transcript_source = "youtube"`, skip Whisper entirely |
| No captions, Whisper disabled (`None`) | `has_transcript: false`, `transcript_source: null` |
| No captions, Whisper enabled, audio download fails | `has_transcript: false`, `transcript_source: null`, continue to next video |
| No captions, Whisper enabled, transcription fails | `has_transcript: false`, `transcript_source: null`, continue to next video |
| Invalid `whisper_model` value | `ValueError` raised in `whisper_transcriber.py` |
| `whisper_model` is `None` | No Whisper import, no audio download — identical to current behavior |

---

## Verification

1. **No regression**: Call `fetch_channel_transcripts(url, "en")` without `whisper_model` — identical to before
2. **Whisper fallback**: Call with `whisper_model="tiny"` on a channel with no captions — videos should get `transcript_source: "whisper"`
3. **Mixed results**: Channel with some captioned and some not — verify correct source labels
4. **Audio cleanup**: After transcription, `.audio_cache/` should not contain leftover `.mp3` files
5. **Model caching**: Second video transcription should be faster than first (model already loaded)

## Definition of Done

- [ ] `src/whisper_transcriber.py` exists with `download_audio()`, `transcribe_audio()`, `whisper_transcript()`
- [ ] Model is cached at module level (loaded once per process)
- [ ] Audio files are cleaned up after transcription
- [ ] `src/fetcher.py` has `fetch_transcript_with_fallback()` returning `(text, source)`
- [ ] `src/service.py` accepts `whisper_model` param and yields `transcript_source` in events
- [ ] Done event includes `with_whisper` count
- [ ] `requirements.txt` includes `faster-whisper`
- [ ] `.gitignore` includes `.audio_cache/`
- [ ] Existing behavior unchanged when `whisper_model` is `None`
