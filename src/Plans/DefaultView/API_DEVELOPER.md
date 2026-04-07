# API Developer — Default Transcript View on Load

## Goal

Add a `GET /api/transcripts` endpoint to `web/api.py` that returns all saved transcript entries from the index, enabling the frontend to populate the video table on page load.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/api.py` |

## Blocked By

Nothing — can start immediately.

## Delivers

A REST endpoint that lists all saved transcripts as JSON, matching the frontend `VideoInfo` shape.

---

## Detailed Steps

### 1. Add the endpoint to `web/api.py`

**IMPORTANT**: This route must be defined BEFORE the existing `GET /api/transcripts/{video_id}` route. Otherwise, FastAPI will match the literal path `/api/transcripts` to the `{video_id}` parameter and treat `"transcripts"` as a video ID.

Add this endpoint between the `POST /api/fetch-transcripts` and `GET /api/transcripts/{video_id}` routes:

```python
@app.get("/api/transcripts")
async def list_transcripts():
    from src.storage import load_index

    try:
        index = load_index("./transcripts")
    except FileNotFoundError:
        return {"videos": [], "total": 0, "with_transcript": 0}

    videos = [
        {
            "video_id": entry["video_id"],
            "title": entry["title"],
            "url": entry["url"],
            "duration": entry.get("duration"),
            "upload_date": entry.get("upload_date"),
            "has_transcript": entry.get("has_transcript", False),
            "transcript_source": "youtube" if entry.get("has_transcript") else None,
        }
        for entry in index
    ]

    with_transcript = sum(1 for v in videos if v["has_transcript"])

    return {
        "videos": videos,
        "total": len(videos),
        "with_transcript": with_transcript,
    }
```

Key design decisions:
- Uses existing `load_index()` from `src.storage` — no new backend code needed
- Maps index entries to match the frontend `VideoInfo` interface shape
- Adds `transcript_source: "youtube"` for entries where `has_transcript` is true (the index doesn't store this field, but all transcripts were fetched from YouTube captions)
- Uses `.get()` with defaults for optional fields (`duration`, `upload_date`) — handles older index entries gracefully
- Returns empty result (not 404) when no index exists — the app should load clean, not error

---

## Expected Final State

### `web/api.py` — endpoint order

The file will have four endpoints in this order:
1. `GET /api/health` — health check
2. `POST /api/fetch-transcripts` — SSE stream for fetching
3. `GET /api/transcripts` — list all saved transcripts *(new)*
4. `GET /api/transcripts/{video_id}` — serve single transcript content *(existing)*

The order matters — `GET /api/transcripts` must come before `GET /api/transcripts/{video_id}`.

---

## Verification

1. With existing transcripts:
   ```bash
   curl http://localhost:8000/api/transcripts
   ```
   Expected: JSON with `videos` array, `total`, and `with_transcript` count

2. With no transcripts folder:
   ```bash
   rm transcripts/_index.json
   curl http://localhost:8000/api/transcripts
   ```
   Expected: `{"videos":[],"total":0,"with_transcript":0}`

3. Existing single-transcript endpoint still works:
   ```bash
   curl http://localhost:8000/api/transcripts/rGLXc1GmsaI
   ```
   Expected: JSON with `video_id`, `title`, `content`

4. Health endpoint still works:
   ```bash
   curl http://localhost:8000/api/health
   ```
   Expected: `{"status":"ok"}`
