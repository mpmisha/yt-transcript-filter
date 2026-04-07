# API Developer — Skip Already-Fetched Transcripts

## Goal

No changes needed for the API layer.

## Rationale

The API layer (`web/api.py`) streams whatever events the service layer yields. The new `"cached"` step and `"cached"` transcript source are just string values in the SSE JSON — no schema validation or Pydantic model changes needed.

The `GET /api/transcripts` listing endpoint already reads `_index.json` as-is, so the merged index works automatically.

## Files

No files to modify.

## Verification

1. Start the API, fetch a channel, re-fetch → SSE events include `"cached"` step and source
2. `GET /api/transcripts` returns all entries including previously cached ones
