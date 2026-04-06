# API Developer — FastAPI Endpoints

## Goal

Create a thin FastAPI HTTP layer that exposes the BE service as a Server-Sent Events (SSE) stream. The API validates input, calls the service generator, and formats each yielded dict as an SSE event.

## Files

| Action | File |
|--------|------|
| **Create** | `web/api.py` |
| **Create** | `web/requirements.txt` |
| Reference (read-only) | `src/service.py` — `fetch_channel_transcripts()` generator (from BE Dev) |

## Blocked By

**BE Developer** — needs `src/service.py` with the `fetch_channel_transcripts()` generator interface. Can stub the generator locally to start early.

## Delivers

Working SSE endpoint at `POST /api/fetch-transcripts` for the FE Developer to integrate against.

---

## Detailed Steps

### 1. Create `web/requirements.txt`

```
fastapi>=0.110.0
uvicorn>=0.29.0
```

### 2. Create `web/api.py`

#### App Setup

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
import json

app = FastAPI(title="yt-transcript-filter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Request Model

```python
class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
```

#### Health Endpoint

```python
@app.get("/api/health")
def health():
    return {"status": "ok"}
```

#### Fetch Transcripts Endpoint

```python
@app.post("/api/fetch-transcripts")
async def fetch_transcripts(req: FetchRequest):
    if not req.url.strip():
        return JSONResponse(status_code=400, content={"detail": "URL is required"})

    def event_stream():
        try:
            from src.service import fetch_channel_transcripts
            for event in fetch_channel_transcripts(req.url, req.lang):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'event': 'error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

### 3. Input Validation

| Field | Validation | Error |
|-------|-----------|-------|
| `url` | Must not be empty/whitespace | 400: `"URL is required"` |
| `lang` | Optional, defaults to `"en"`. Accept any string (language codes are validated downstream by `youtube-transcript-api`) | — |

### 4. Error Handling

| Source | Error Type | Response |
|--------|-----------|----------|
| Empty URL | Client error | HTTP 400: `{"detail": "URL is required"}` |
| Bad URL / yt-dlp failure | `ValueError` from service | SSE error event: `{"event": "error", "detail": "..."}` |
| Unexpected failure | `Exception` | SSE error event: `{"event": "error", "detail": "Internal server error"}` |

> **Note**: Errors that occur _during_ streaming (after headers are sent) cannot change the HTTP status code. They are sent as SSE error events instead. Pre-stream validation errors (empty URL) return proper HTTP error codes.

### 5. Verify

**Start the server:**
```bash
cd /path/to/yt-transcript-filter
uvicorn web.api:app --reload --port 8000
```

**Test health:**
```bash
curl http://localhost:8000/api/health
# {"status":"ok"}
```

**Test fetch (small playlist):**
```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en"}'
```

**Expected output (streamed):**
```
data: {"event":"progress","current":1,"total":3,"video_id":"abc","title":"...","duration":120,"upload_date":"20240115","url":"https://...","has_transcript":true}

data: {"event":"progress","current":2,"total":3,...}

data: {"event":"progress","current":3,"total":3,...}

data: {"event":"done","total":3,"with_transcript":2,"output_dir":"./transcripts"}

```

**Test validation:**
```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"","lang":"en"}'
# {"detail":"URL is required"}
```

---

## Stubbing (if starting before BE Dev is done)

If you want to start before `src/service.py` is ready, create a temporary stub:

```python
# Temporary stub in web/api.py for development
import time

def _stub_generator(url, lang):
    total = 3
    for i in range(total):
        time.sleep(1)  # simulate work
        yield {
            "event": "progress",
            "current": i + 1,
            "total": total,
            "video_id": f"stub_{i}",
            "title": f"Stub Video {i + 1}",
            "duration": 120 + i * 60,
            "upload_date": "20240115",
            "url": f"https://www.youtube.com/watch?v=stub_{i}",
            "has_transcript": i != 1,  # second video has no transcript
        }
    yield {"event": "done", "total": total, "with_transcript": 2, "output_dir": "./transcripts"}
```

Replace with the real import once BE Dev delivers.

---

## Definition of Done

- [ ] `web/requirements.txt` exists with `fastapi` and `uvicorn`
- [ ] `web/api.py` exists with CORS middleware configured
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `POST /api/fetch-transcripts` validates input and streams SSE events
- [ ] Empty URL returns HTTP 400
- [ ] Service errors are caught and sent as SSE error events
- [ ] Manual curl test with a real playlist streams events correctly
- [ ] Response `Content-Type` is `text/event-stream`
