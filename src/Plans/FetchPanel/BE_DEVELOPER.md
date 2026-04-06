# BE Developer — Python Service Layer

## Goal

Create a generator-based service function that wraps the existing `fetcher` and `storage` modules into a single interface the API layer can consume. This decouples the HTTP layer from the business logic.

## Files

| Action | File |
|--------|------|
| **Create** | `src/service.py` |
| Reference (read-only) | `src/fetcher.py` — `get_video_list()`, `fetch_transcript()`, `VideoInfo` |
| Reference (read-only) | `src/storage.py` — `save_transcripts()` |

## Blocked By

Nothing — can start immediately.

## Delivers

`fetch_channel_transcripts()` generator function for the API Developer to consume.

---

## Detailed Steps

### 1. Create `src/service.py`

Implement a single generator function:

```python
def fetch_channel_transcripts(url: str, lang: str = "en") -> Generator[dict, None, None]:
```

**Flow:**

1. Call `get_video_list(url)` to get the list of `VideoInfo` objects
2. Determine `total = len(videos)`
3. For each video (index `i`):
   - Call `fetch_transcript(video.video_id, languages=[lang])`
   - Set `video.transcript` to the result (or `None` on failure)
   - Yield a progress dict:
     ```python
     {
         "event": "progress",
         "current": i + 1,
         "total": total,
         "video_id": video.video_id,
         "title": video.title,
         "duration": video.duration,
         "upload_date": video.upload_date,
         "url": video.url,
         "has_transcript": video.transcript is not None,
     }
     ```
4. After the loop, call `save_transcripts(videos, "./transcripts")`
5. Yield a done dict:
   ```python
   {
       "event": "done",
       "total": total,
       "with_transcript": sum(1 for v in videos if v.transcript),
       "output_dir": "./transcripts",
   }
   ```

### 2. Error Handling

| Scenario | Behavior |
|----------|----------|
| Invalid URL / `yt-dlp` failure | `get_video_list()` will raise `subprocess.CalledProcessError`. Catch it and raise `ValueError("Failed to fetch video list from URL: {url}")` |
| Single transcript unavailable | `fetch_transcript()` returns `None`. Yield the video with `has_transcript: false` and **continue** to the next video — don't crash the batch |
| Empty video list | Yield a done event with `total: 0, with_transcript: 0` |

### 3. Verify

Create a quick test script (don't commit, just for manual testing):

```python
# test_service.py
from src.service import fetch_channel_transcripts

url = "https://www.youtube.com/playlist?list=PLxxxxxx"  # small 3-video playlist
for event in fetch_channel_transcripts(url, lang="en"):
    print(event)
```

**Expected output:**
```
{'event': 'progress', 'current': 1, 'total': 3, 'video_id': '...', 'title': '...', 'duration': 120, 'upload_date': '20240115', 'url': 'https://...', 'has_transcript': True}
{'event': 'progress', 'current': 2, 'total': 3, ...}
{'event': 'progress', 'current': 3, 'total': 3, ...}
{'event': 'done', 'total': 3, 'with_transcript': 2, 'output_dir': './transcripts'}
```

---

## Existing Code Reference

### `get_video_list()` (from `src/fetcher.py`)

```python
def get_video_list(channel_or_playlist_url: str) -> list[VideoInfo]:
    # Runs: yt-dlp --flat-playlist --dump-json <url>
    # Returns list of VideoInfo(video_id, title, url, duration, upload_date, description)
```

### `fetch_transcript()` (from `src/fetcher.py`)

```python
def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
    # Uses youtube_transcript_api to get captions
    # Returns full transcript as string, or None if unavailable
```

### `save_transcripts()` (from `src/storage.py`)

```python
def save_transcripts(videos: list[VideoInfo], output_dir: str | Path) -> Path:
    # Saves one .txt per video + _index.json metadata
    # Returns the output directory path
```

---

## Definition of Done

- [ ] `src/service.py` exists with `fetch_channel_transcripts()` generator
- [ ] Generator yields correct progress dicts matching the shared contract format
- [ ] Per-video failures are handled gracefully (no crash, yields `has_transcript: false`)
- [ ] Invalid URL raises `ValueError` with a clear message
- [ ] Manual test with a real playlist produces expected output
- [ ] Transcripts are saved to `./transcripts/` with `_index.json`
