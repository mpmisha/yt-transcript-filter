# BE Developer — Skip Already-Fetched Transcripts

## Goal

Add cache-aware transcript fetching to the service layer. Before calling the YouTube transcript API, check if a transcript already exists locally. If it does, skip the API call. Also add a helper to extract transcript body from `.md` files.

## Files

| Action | File |
|--------|------|
| **Modify** | `src/storage.py` |
| **Modify** | `src/service.py` |

## Blocked By

Nothing — can start immediately.

## Delivers

Re-scraping a channel skips already-fetched transcripts, only calling the API for new or previously-failed videos.

---

## Detailed Steps

### 1. Add `extract_transcript_body()` to `src/storage.py`

Add this function after `load_transcript()`:

```python
def extract_transcript_body(output_dir: str | Path, filename: str) -> str | None:
    """Extract the transcript body from a Markdown transcript file.

    Strips the metadata header (everything before and including the '---' separator).
    Returns the body text, or None if the file doesn't exist or has no content after the header.
    """
    filepath = Path(output_dir) / filename
    if not filepath.exists():
        return None

    text = filepath.read_text(encoding="utf-8")
    separator = "\n---\n"
    idx = text.find(separator)
    if idx == -1:
        return None

    body = text[idx + len(separator):].strip()
    return body if body else None
```

This function:
- Returns `None` if the file doesn't exist (not an error — just means not cached)
- Returns `None` if there's no body after the `---` separator (metadata-only file)
- Returns the raw transcript text body (paragraphs separated by blank lines)

### 2. Update `src/service.py` — add cache-aware logic

#### 2a. Update imports

**Before:**
```python
from .fetcher import fetch_transcript, get_video_list
from .storage import save_transcripts
```

**After:**
```python
import json
from pathlib import Path

from .fetcher import fetch_transcript, get_video_list
from .storage import extract_transcript_body, load_index, save_transcripts
```

#### 2b. Add index loading after video list is built

Insert after `total = len(videos)` and before the `yield video_list` event:

```python
    # Load existing index to check for cached transcripts
    output_dir = "./transcripts"
    cached_entries: dict[str, dict] = {}
    _original_index: list[dict] = []
    try:
        _original_index = load_index(output_dir)
        cached_entries = {
            entry["video_id"]: entry
            for entry in _original_index
            if entry.get("has_transcript")
        }
    except FileNotFoundError:
        pass  # No index yet — all videos need fetching
```

#### 2c. Replace the per-video fetch loop

Replace the current loop (from `for i, video in enumerate(videos):` through the `time.sleep(1.5)`) with:

```python
    last_was_api_call = False

    for i, video in enumerate(videos):
        transcript_source: str | None = None
        cached_entry = cached_entries.get(video.video_id)

        if cached_entry:
            # Check if we can load the cached transcript body
            body = extract_transcript_body(output_dir, cached_entry["file"])
            if body is not None:
                yield {"event": "video_status", "video_id": video.video_id, "step": "cached"}
                video.transcript = body
                transcript_source = "cached"
                last_was_api_call = False
            else:
                # File missing or no transcript body — re-fetch
                cached_entry = None

        if cached_entry is None:
            # Rate limit: sleep between consecutive API calls only
            if last_was_api_call:
                time.sleep(1.5)

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

            last_was_api_call = True

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

Key design decisions:
- `last_was_api_call` tracks whether the previous iteration hit the API, so sleep only happens between consecutive API calls
- If a cached entry exists but `extract_transcript_body()` returns `None`, fall through to the normal fetch path
- Cached videos emit a single `"cached"` step (no `checking_captions`/`captions_found` sequence)

#### 2d. Replace the save block with merge-aware logic

**Before:**
```python
    if videos:
        save_transcripts(videos, "./transcripts")
```

**After:**
```python
    if videos:
        save_transcripts(videos, output_dir)

        # Merge: preserve index entries for videos NOT in the current batch
        current_ids = {v.video_id for v in videos}
        extra_entries = [
            entry for entry in _original_index
            if entry["video_id"] not in current_ids
        ]
        if extra_entries:
            new_index = load_index(output_dir)
            new_index.extend(extra_entries)
            index_path = Path(output_dir) / "_index.json"
            index_path.write_text(
                json.dumps(new_index, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
```

This uses `_original_index` (the full pre-fetch snapshot) to find entries for video IDs NOT in the current batch, then appends them to the freshly-written index.

---

## Verification

1. Fetch a channel → all videos fetched from API, transcripts saved
2. Fetch same channel again → all videos show "cached" step, no API calls, no 1.5s delays
3. Fetch same channel with higher limit → new videos fetched normally, existing ones cached
4. Videos with `has_transcript: false` → re-fetched (not cached)
5. First-ever fetch (no `_index.json`) → works without errors
6. `_index.json` after re-fetch preserves entries from other channels not in current batch
