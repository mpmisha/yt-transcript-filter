# API Developer — Topic Filter SSE Endpoint

## Goal

Add a `POST /api/filter-by-topic` SSE endpoint that accepts a topic string and streams Gemini-scored relevance results for all fetched transcripts.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/api.py` |

## Blocked By

**BE Developer** — needs Task 1 complete so `filter_by_topic()` generator exists in `src/llm_filter.py`.

## Delivers

A new SSE endpoint that streams `filter_start`, `filter_progress`, `filter_done`, and `filter_error` events.

---

## Detailed Steps

### 1. Add `FilterRequest` Pydantic model

Add below the existing `FetchRequest` model:

```python
class FilterRequest(BaseModel):
    topic: str
    threshold: int = Field(default=5, ge=0, le=10)
    output_dir: str = "./transcripts"
```

### 2. Add `POST /api/filter-by-topic` endpoint

Add after the existing `/api/transcripts/{video_id}` endpoint:

```python
@app.post("/api/filter-by-topic")
async def filter_by_topic_endpoint(req: FilterRequest):
    if not req.topic.strip():
        return JSONResponse(status_code=400, content={"detail": "Topic is required"})

    def event_stream():
        try:
            from src.llm_filter import filter_by_topic
            for event in filter_by_topic(req.output_dir, req.topic.strip(), threshold=req.threshold):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'filter_error', 'detail': str(e)})}\n\n"
        except Exception:
            logging.getLogger(__name__).exception("Unhandled error in filter-by-topic stream")
            yield f"data: {json.dumps({'event': 'filter_error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

Key details:
- Uses the same `StreamingResponse` + SSE pattern as the existing `fetch-transcripts` endpoint
- Lazy-imports `filter_by_topic` from `src.llm_filter` (same pattern as existing `fetch_channel_transcripts` import)
- `ValueError` is caught specifically — this is what `_configure_gemini()` raises when `GEMINI_API_KEY` is missing
- The `filter_error` event name matches the SSE contract (not `error`)

### 3. No other changes needed

The existing CORS middleware and FastAPI setup already cover the new endpoint. No new imports are required at the module level.

---

## Expected Final State

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import json
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="yt-transcript-filter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    limit: Optional[int] = Field(default=None, ge=1)


class FilterRequest(BaseModel):
    topic: str
    threshold: int = Field(default=5, ge=0, le=10)
    output_dir: str = "./transcripts"


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/fetch-transcripts")
async def fetch_transcripts(req: FetchRequest):
    if not req.url.strip():
        return JSONResponse(status_code=400, content={"detail": "URL is required"})

    def event_stream():
        try:
            from src.service import fetch_channel_transcripts
            for event in fetch_channel_transcripts(req.url, req.lang, limit=req.limit):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"
        except Exception:
            logging.getLogger(__name__).exception("Unhandled error in fetch-transcripts stream")
            yield f"data: {json.dumps({'event': 'error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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


@app.post("/api/filter-by-topic")
async def filter_by_topic_endpoint(req: FilterRequest):
    if not req.topic.strip():
        return JSONResponse(status_code=400, content={"detail": "Topic is required"})

    def event_stream():
        try:
            from src.llm_filter import filter_by_topic
            for event in filter_by_topic(req.output_dir, req.topic.strip(), threshold=req.threshold):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'filter_error', 'detail': str(e)})}\n\n"
        except Exception:
            logging.getLogger(__name__).exception("Unhandled error in filter-by-topic stream")
            yield f"data: {json.dumps({'event': 'filter_error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## Verification

1. Start the API server: `uvicorn web.api:app --reload --port 8000`
2. Test health: `curl http://localhost:8000/api/health`
3. Test missing topic validation:
   ```bash
   curl -X POST http://localhost:8000/api/filter-by-topic \
     -H "Content-Type: application/json" \
     -d '{"topic": ""}'
   ```
   → should return 400 `{"detail": "Topic is required"}`
4. Test with valid topic (requires `GEMINI_API_KEY` and existing transcripts):
   ```bash
   curl -N -X POST http://localhost:8000/api/filter-by-topic \
     -H "Content-Type: application/json" \
     -d '{"topic": "app monetization"}'
   ```
   → should stream SSE events
5. `grep -c "filter" web/api.py` — should show the new endpoint code
