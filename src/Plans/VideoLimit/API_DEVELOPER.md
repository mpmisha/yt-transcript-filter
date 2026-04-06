# API Developer — Video Limit

## Goal

Add an optional `limit` field to the `FetchRequest` Pydantic model, validate it, and pass it through to the service layer.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/api.py` — add `limit` field to `FetchRequest`, validate, pass to service |

## Blocked By

**BE Developer** — needs `src/service.py` to accept the `limit` parameter.

## Delivers

API endpoint that accepts and validates an optional `limit` field in the request body.

---

## Detailed Steps

### 1. Add `limit` to `FetchRequest`

Current:
```python
class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    whisper_model: Optional[str] = None
```

New:
```python
from pydantic import Field

class FetchRequest(BaseModel):
    url: str
    lang: str = "en"
    whisper_model: Optional[str] = None
    limit: Optional[int] = Field(default=None, ge=1)
```

The `ge=1` constraint ensures Pydantic returns a 422 error if `limit` is 0 or negative. No manual validation needed.

### 2. Pass `limit` to the service

Current:
```python
for event in fetch_channel_transcripts(req.url, req.lang, whisper_model=req.whisper_model):
```

New:
```python
for event in fetch_channel_transcripts(req.url, req.lang, whisper_model=req.whisper_model, limit=req.limit):
```

---

## What NOT to Change

- No changes to health endpoint.
- No changes to CORS, error handling, or streaming logic.
- No changes to Whisper model validation (already handled).

---

## Verification

### 1. Valid limit

```bash
curl -N -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en","limit":3}'
```

**Expected**: SSE stream with `video_list` showing 3 videos, 3 `progress` events, `done` with `total: 3`.

### 2. No limit (backwards-compatible)

```bash
curl -N -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en"}'
```

**Expected**: All videos processed (same as before).

### 3. Invalid limit (zero)

```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","limit":0}'
```

**Expected**: HTTP 422 with Pydantic validation error.

### 4. Invalid limit (negative)

```bash
curl -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","limit":-5}'
```

**Expected**: HTTP 422 with Pydantic validation error.

### 5. Limit with Whisper

```bash
curl -N -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","whisper_model":"tiny","limit":2}'
```

**Expected**: Only 2 videos processed with Whisper fallback.

---

## Checklist

- [ ] `limit: Optional[int] = Field(default=None, ge=1)` added to `FetchRequest`
- [ ] `limit=req.limit` passed to `fetch_channel_transcripts()`
- [ ] `limit: 0` returns 422
- [ ] `limit: -1` returns 422
- [ ] Omitting `limit` processes all videos (backwards-compatible)
- [ ] No changes to other endpoints or middleware
