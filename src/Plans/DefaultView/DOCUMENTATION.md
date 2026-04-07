# Documentation Agent — Default Transcript View on Load

## Goal

After all code changes are implemented, update project documentation to reflect the new auto-load behavior.

## When to Run

After Task 2 (API Developer) and Task 3 (FE Developer) are complete and verified.

## Trigger

Run `@documentation` with context: "The DefaultView plan has been implemented. Update docs."

## What to Update

### 1. README.md

- Mention that the app auto-loads existing transcripts on startup
- Add the new `GET /api/transcripts` endpoint to any API documentation section

### 2. docs/DEVELOPMENT_LOG.md

Append a new entry:
```markdown
## Default Transcript View on Load
**Date**: {today's date}
**Plan**: `src/Plans/DefaultView/PLAN.md`

### Summary
The app now auto-loads existing transcripts from `_index.json` when the page loads. If transcripts have been previously fetched, the video table and summary card appear immediately — no need to re-fetch.

### Changes
- **Files modified**: `web/api.py`, `web/frontend/src/hooks/useFetchTranscripts.ts`
- **New endpoint**: `GET /api/transcripts` — returns all saved transcript entries from the index
- **Hook update**: `useFetchTranscripts` now calls `loadExisting()` on mount via `useEffect`

### Technical Details
- API reads `_index.json` via existing `load_index()` from `src/storage.py`
- Response maps index entries to match frontend `VideoInfo` shape, adding `transcript_source` field
- `GET /api/transcripts` must be defined before `GET /api/transcripts/{video_id}` in route order
- Silently degrades to empty state if no transcripts exist or API is unreachable
- Starting a new fetch replaces the pre-loaded data
```

### 3. web/frontend/README.md

No changes needed (no new dependencies or build steps).

## Reference

- Plan file: `src/Plans/DefaultView/PLAN.md`
- API implementation: `web/api.py`
- Frontend implementation: `web/frontend/src/hooks/useFetchTranscripts.ts`
