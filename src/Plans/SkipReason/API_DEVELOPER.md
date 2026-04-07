# API Developer — Skip Reason Messages + Rate-Limit Short-Circuit

## Goal

No changes needed for the API layer.

## Rationale

The API layer (`web/api.py`) streams whatever events the service layer yields via `StreamingResponse`. The new `error` field on `"skipped"` status events is just an additional string key in the SSE JSON — no schema validation or Pydantic model changes are needed.

The `POST /api/fetch-transcripts` endpoint serializes each event dict with `json.dumps()` in `event_stream()`, so the `error` field flows through automatically.

## Files

No files to modify.

## Verification

1. Start the API, fetch a channel with unavailable transcripts → SSE events include `"error": "..."` on skipped events
2. Simulate rate limit → skipped events include the rate-limit reason strings
3. `GET /api/transcripts` is unaffected (returns `_index.json` data, which has no skip reasons)
