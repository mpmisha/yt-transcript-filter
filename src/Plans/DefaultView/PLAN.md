# Default Transcript View on Load — Development Plan

## Overview

When the app loads, if transcripts already exist in `transcripts/_index.json`, show them in the video table immediately — the same grid view as after a fetch completes. No need to run a fetch first.

## Motivation

- Users who have previously fetched transcripts must currently re-fetch to see them in the UI
- The transcript files and index already exist on disk — the app should surface them automatically
- Provides immediate value on page load without any user action

## Architecture Change

```
Current:  app loads → empty state → user triggers fetch → table appears
New:      app loads → GET /api/transcripts → table appears immediately (if index exists)
```

New data flow on app load:
```
App mounts → useFetchTranscripts hook → useEffect calls loadExisting()
  → GET /api/transcripts → API reads _index.json via load_index()
  → JSON { videos, total, with_transcript } → hook sets videos + status "done"
  → VideoTable + SummaryCard render immediately
```

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: No changes needed.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

### Task 2 → Delegate to `@api-developer`

**API Developer**: Add a GET endpoint to list all saved transcripts from the index.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- **Modify** `web/api.py` — add `GET /api/transcripts` endpoint

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Add auto-load of existing transcripts on app mount.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/hooks/useFetchTranscripts.ts` — add `loadExisting()` + `useEffect` on mount

### Task 4 → Delegate to `@documentation`

**Documentation Agent**: After Tasks 2–3 are complete, update project documentation.

Full specification: [DOCUMENTATION.md](DOCUMENTATION.md)

## Dependency Graph

```
Task 1 (BE Dev) — no changes
Task 2 (API Dev) ──▶ Task 3 (FE Dev) ──▶ Task 4 (Documentation)
```

- **Task 2** (API) has no dependencies — can start immediately
- **Task 3** (FE) depends on Task 2 (needs the endpoint to fetch from)
- **Task 4** (Documentation) runs after Tasks 2–3 are complete

## Shared Contract

### API Endpoint

**`GET /api/transcripts`**

Success response (200):
```json
{
  "videos": [
    {
      "video_id": "rGLXc1GmsaI",
      "title": "One Deal Took This App From $300 to $35K/Month",
      "url": "https://www.youtube.com/watch?v=rGLXc1GmsaI",
      "duration": null,
      "upload_date": null,
      "has_transcript": true,
      "transcript_source": "youtube"
    }
  ],
  "total": 1,
  "with_transcript": 1
}
```

Empty response (200) — when no index exists:
```json
{
  "videos": [],
  "total": 0,
  "with_transcript": 0
}
```

### Frontend State After Load

After `loadExisting()` completes with data:
- `videos` → populated array from API response
- `progress` → `{ current: total, total: total }`
- `withTranscript` → count from API
- `status` → `"done"`
- `videoProgress` → empty (no active fetch)

## Design Decisions

- **Status set to `"done"`** — shows `SummaryCard` with transcript count, consistent with post-fetch state
- **`transcript_source` defaults to `"youtube"`** for entries where `has_transcript` is true — the index doesn't store this field, but all current transcripts come from YouTube captions
- **No progress bar or video progress list** on initial load — those are only for active fetches
- **New fetch replaces loaded data** — `startFetch` already resets all state before starting
- **`GET /api/transcripts`** route must be defined BEFORE `GET /api/transcripts/{video_id}`** in `web/api.py` — otherwise FastAPI matches the literal path segment "transcripts" to the `{video_id}` parameter

## Verification

1. `curl http://localhost:8000/api/transcripts` → JSON with all saved videos
2. Open the app fresh → table appears immediately with existing transcripts
3. `SummaryCard` shows correct transcript count
4. "View" button works on pre-loaded transcripts
5. Starting a new fetch replaces the loaded data and works normally
6. If `transcripts/` folder is empty or missing → app loads normally with empty state
