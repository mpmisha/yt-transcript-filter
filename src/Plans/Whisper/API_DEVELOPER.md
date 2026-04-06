# API Developer — Whisper Model Parameter

## Goal

Extend the FastAPI endpoint to accept an optional `whisper_model` parameter, validate it against allowed values, and pass it through to the BE service layer.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/api.py` — add `whisper_model` to request model, validate, pass to service |

## Blocked By

**BE Developer** — needs the updated `fetch_channel_transcripts(url, lang, whisper_model)` signature in `src/service.py`.

## Delivers

Updated `POST /api/fetch-transcripts` endpoint that accepts `whisper_model` and streams events with `transcript_source`.

---

## Detailed Steps

### 1. Update `FetchRequest` Pydantic Model

**Current:**
```python
class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
```

**New:**
```python
from typing import Literal

VALID_WHISPER_MODELS = ("tiny", "base", "small", "medium")

class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    whisper_model: str | None = None
```

### 2. Add Validation for `whisper_model`

In the `fetch_transcripts` endpoint, after the existing URL validation, add:

```python
if req.whisper_model is not None and req.whisper_model not in VALID_WHISPER_MODELS:
    return JSONResponse(
        status_code=400,
        content={"detail": f"Invalid whisper_model. Must be one of: {', '.join(VALID_WHISPER_MODELS)}"},
    )
```

### 3. Pass `whisper_model` to Service

**Current call:**
```python
for event in fetch_channel_transcripts(req.url, req.lang):
```

**New call:**
```python
for event in fetch_channel_transcripts(req.url, req.lang, whisper_model=req.whisper_model):
```

### 4. Complete Updated Endpoint

For clarity, the full updated endpoint should look like:

```python
VALID_WHISPER_MODELS = ("tiny", "base", "small", "medium")

@app.post("/api/fetch-transcripts")
async def fetch_transcripts(req: FetchRequest):
    if not req.url.strip():
        return JSONResponse(status_code=400, content={"detail": "URL is required"})

    if req.whisper_model is not None and req.whisper_model not in VALID_WHISPER_MODELS:
        return JSONResponse(
            status_code=400,
            content={"detail": f"Invalid whisper_model. Must be one of: {', '.join(VALID_WHISPER_MODELS)}"},
        )

    def event_stream():
        try:
            from src.service import fetch_channel_transcripts
            for event in fetch_channel_transcripts(req.url, req.lang, whisper_model=req.whisper_model):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as e:
            yield f"data: {json.dumps({'event': 'error', 'detail': str(e)})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'event': 'error', 'detail': 'Internal server error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

---

## Input Validation Summary

| Field | Validation | Error |
|-------|-----------|-------|
| `url` | Must not be empty/whitespace | 400: `"URL is required"` |
| `lang` | Optional, defaults to `"en"` | — |
| `whisper_model` | Must be `null` or one of `"tiny"`, `"base"`, `"small"`, `"medium"` | 400: `"Invalid whisper_model. Must be one of: tiny, base, small, medium"` |

---

## Verification

**Test without whisper_model (backwards compatible):**
```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en"}'
```

**Test with whisper_model:**
```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en","whisper_model":"base"}'
```

**Test invalid whisper_model:**
```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en","whisper_model":"invalid"}'
# Expected: {"detail":"Invalid whisper_model. Must be one of: tiny, base, small, medium"}
```

**Test null whisper_model (explicit):**
```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en","whisper_model":null}'
# Expected: streams normally without Whisper, same as omitting the field
```

**Verify SSE events include `transcript_source`:**
- Progress events should have `"transcript_source": "youtube"` or `"transcript_source": "whisper"` or `"transcript_source": null`
- Done event should have `"with_whisper": N`

---

## Definition of Done

- [ ] `FetchRequest` model includes `whisper_model: str | None = None`
- [ ] Invalid `whisper_model` values return HTTP 400 with clear message
- [ ] `null` or omitted `whisper_model` works identically to current behavior
- [ ] `whisper_model` is passed to `fetch_channel_transcripts()` in the service call
- [ ] Curl tests pass for all scenarios above
