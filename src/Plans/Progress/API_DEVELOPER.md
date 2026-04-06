# API Developer — Detailed Progress Events (Verification Only)

## Goal

Verify that the new `video_list` and `video_status` SSE events from the BE Developer stream correctly through the existing FastAPI endpoint. **No code changes are required** — the current `StreamingResponse` already forwards all yielded dicts.

## Files

| Action | File |
|--------|------|
| Verify (no changes) | `web/api.py` |

## Blocked By

**BE Developer** — needs the updated `src/service.py` that yields the new events.

## Delivers

Confirmation that all new event types stream correctly via SSE.

---

## Why No Code Changes

The current endpoint implementation:

```python
def event_stream():
    for event in fetch_channel_transcripts(req.url, req.lang, whisper_model=req.whisper_model):
        yield f"data: {json.dumps(event)}\n\n"
```

This iterates the generator and converts every yielded dict to an SSE `data:` line. Since the BE Developer is adding new dicts (`video_list`, `video_status`) to the same generator, they automatically stream through without any API changes.

---

## Verification Steps

### 1. Start the server

```bash
uvicorn web.api:app --reload --port 8000
```

### 2. Test with curl (Whisper disabled)

```bash
curl -N -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en"}'
```

**Expected output** (order matters):

```
data: {"event":"video_list","total":3,"videos":[...]}

data: {"event":"video_status","video_id":"abc","step":"checking_captions"}
data: {"event":"video_status","video_id":"abc","step":"captions_found"}
data: {"event":"progress","current":1,"total":3,...}

data: {"event":"video_status","video_id":"def","step":"checking_captions"}
data: {"event":"video_status","video_id":"def","step":"no_captions"}
data: {"event":"video_status","video_id":"def","step":"skipped"}
data: {"event":"progress","current":2,"total":3,...}

data: {"event":"done","total":3,...}
```

### 3. Test with curl (Whisper enabled)

```bash
curl -N -X POST http://localhost:8000/api/fetch-transcripts \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/playlist?list=PLxxxxxx","lang":"en","whisper_model":"tiny"}'
```

**Verify** that for videos without captions:
- `{"event":"video_status","video_id":"...","step":"downloading_audio"}` appears
- `{"event":"video_status","video_id":"...","step":"transcribing"}` appears
- `{"event":"video_status","video_id":"...","step":"whisper_complete"}` or `whisper_failed` appears
- Each of these events arrives **as it happens** (not batched at the end)

### 4. Verify real-time streaming

Use curl with `-N` (no buffering) and confirm that:
- The `video_list` event arrives immediately (within 1-2 seconds of clicking)
- `video_status` events for each video arrive in real time
- There is a visible delay between `downloading_audio` and `transcribing` (audio download takes time)
- The stream does not wait until all videos are processed

### 5. Verify backwards compatibility

- All existing fields in `progress` and `done` events are present and unchanged
- The `error` event format is unchanged
- Empty URL still returns HTTP 400
- Invalid `whisper_model` still returns HTTP 400

---

## Checklist

- [ ] New `video_list` events appear in curl output
- [ ] New `video_status` events appear in curl output
- [ ] Events arrive in real-time (not batched)
- [ ] Event order is correct: `video_list` → (`video_status`* → `progress`)* → `done`
- [ ] Existing `progress`, `done`, `error` events unchanged
- [ ] No code changes needed in `web/api.py`
