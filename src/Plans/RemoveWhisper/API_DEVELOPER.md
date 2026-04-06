# API Developer — Remove Whisper from API Layer

## Goal

Remove the `whisper_model` field from the API request model, remove Whisper validation logic, and update the service call to no longer pass `whisper_model`.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/api.py` |

## Blocked By

**BE Developer** — needs Task 1 complete so `fetch_channel_transcripts()` no longer accepts `whisper_model`.

## Delivers

A simplified API endpoint that no longer accepts or validates `whisper_model` in the request body.

---

## Detailed Steps

### 1. Remove `VALID_WHISPER_MODELS` constant

**Remove:**
```python
VALID_WHISPER_MODELS = ("tiny", "base", "small", "medium")
```

### 2. Remove `whisper_model` from `FetchRequest` Pydantic model

**Before:**
```python
class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    whisper_model: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1)
```

**After:**
```python
class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    limit: Optional[int] = Field(default=None, ge=1)
```

### 3. Remove Whisper validation block from `fetch_transcripts` endpoint

**Remove this entire block:**
```python
    if req.whisper_model is not None and req.whisper_model not in VALID_WHISPER_MODELS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid whisper_model. Must be one of: {', '.join(VALID_WHISPER_MODELS)}"},
        )
```

### 4. Remove `whisper_model` from service call

**Before:**
```python
for event in fetch_channel_transcripts(req.url, req.lang, whisper_model=req.whisper_model, limit=req.limit):
```

**After:**
```python
for event in fetch_channel_transcripts(req.url, req.lang, limit=req.limit):
```

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
```

---

## Verification

1. Start the API server: `uvicorn web.api:app --reload --port 8000`
2. Test health endpoint: `curl http://localhost:8000/api/health` — should return `{"status":"ok"}`
3. Test that `whisper_model` in the request body is ignored (Pydantic will silently drop unknown fields by default)
4. `grep -ri whisper web/api.py` — returns nothing
