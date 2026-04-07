# API Developer — Single Video URL Support

## Goal

No changes needed for the API layer.

## Rationale

The `POST /api/fetch-transcripts` endpoint accepts a `url` string and passes it to `fetch_channel_transcripts()`. It doesn't inspect or validate the URL format beyond checking that it's non-empty. The service layer and fetcher handle the rest.

## Files

No files to modify.

## Verification

1. `POST /api/fetch-transcripts` with a single video URL → SSE stream with one video's events
2. `POST /api/fetch-transcripts` with a channel URL → works as before
