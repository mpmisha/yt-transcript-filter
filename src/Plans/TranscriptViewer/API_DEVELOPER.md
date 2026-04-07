# API Developer — Transcript Viewer

## Goal

Add a `GET /api/transcripts/{video_id}` endpoint to `web/api.py` that serves transcript content by video ID.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/api.py` |

## Blocked By

Nothing — can start immediately.

## Delivers

A REST endpoint that returns transcript content as JSON, enabling the frontend to display transcripts in a modal.

---

## Detailed Steps

### 1. Add the endpoint to `web/api.py`

Add this endpoint after the existing `/api/fetch-transcripts` route:

```python
@app.get("/api/transcripts/{video_id}")
async def get_transcript(video_id: str):
    from src.storage import load_index, load_transcript

    try:
        index = load_index("./transcripts")
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"detail": "Transcript not found"})

    entry = next((e for e in index if e["video_id"] == video_id), None)
    if entry is None:
        return JSONResponse(status_code=404, content={"detail": "Transcript not found"})

    try:
        content = load_transcript("./transcripts", entry["file"])
    except FileNotFoundError:
        return JSONResponse(status_code=404, content={"detail": "Transcript not found"})

    return {
        "video_id": video_id,
        "title": entry["title"],
        "content": content,
    }
```

Key design decisions:
- Uses existing `load_index()` and `load_transcript()` from `src.storage` — no new backend code needed
- Three 404 cases: no index file, video_id not in index, file referenced in index doesn't exist
- Returns raw file content as a string in the `content` field — the frontend displays it as-is
- Lazy import of `src.storage` functions (consistent with existing `fetch_transcripts` endpoint pattern)

### 2. No new Pydantic models needed

The response is a simple dict — FastAPI serializes it to JSON automatically. The 404 response uses the existing `JSONResponse` import and the standard `{"detail": "..."}` pattern already used in the codebase.

---

## Expected Final State

### `web/api.py` — new endpoint added after line 48

The file will have three endpoints:
1. `GET /api/health` — health check
2. `POST /api/fetch-transcripts` — SSE stream for fetching
3. `GET /api/transcripts/{video_id}` — serve transcript content *(new)*

---

## Verification

1. Start the API server:
   ```bash
   cd /Users/mimer/Private/yt-transcript-filter
   uvicorn web.api:app --reload --port 8000
   ```

2. Test with a known transcript:
   ```bash
   curl http://localhost:8000/api/transcripts/rGLXc1GmsaI
   ```
   Expected: JSON with `video_id`, `title`, and `content` fields

3. Test with a nonexistent video:
   ```bash
   curl http://localhost:8000/api/transcripts/nonexistent
   ```
   Expected: `{"detail":"Transcript not found"}` with status 404

4. Test health endpoint still works:
   ```bash
   curl http://localhost:8000/api/health
   ```
   Expected: `{"status":"ok"}`
