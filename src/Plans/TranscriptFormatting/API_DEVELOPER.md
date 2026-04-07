# API Developer — Markdown Transcript Formatting

## Goal

No changes needed for the API layer.

## Rationale

The API streams SSE events with raw transcript text and metadata. Formatting happens at the storage layer (`src/storage.py`), which is called by the service pipeline (`src/service.py`) after all videos are processed. The API does not read or serve saved transcript files.

## Files

No files to modify.

## Verification

1. Verify the API still works after the BE changes: `curl http://localhost:8000/api/health`
2. Fetch a channel via the UI — SSE events stream correctly, transcripts are saved as `.md`
