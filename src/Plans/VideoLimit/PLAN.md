> **Status: ✅ COMPLETED**

# Video Limit — Development Plan

## Overview

Add an optional video limit parameter so users can cap the number of videos processed during a fetch. Useful for testing, quick previews, or avoiding long runs on large channels. The limit is applied after video discovery by slicing the list — minimal, non-invasive, and backwards-compatible.

## What Changes

| Current Behavior | New Behavior |
|-----------------|--------------|
| All discovered videos are processed | User can optionally limit to N videos |
| No limit input in the UI | Number input field next to the language input |
| CLI has no `--limit` flag | `--limit` / `-n` option available |
| API accepts `url`, `lang`, `whisper_model` | API also accepts optional `limit` field |

## Design Decisions

- **Limit applied after discovery** — `get_video_list()` returns all videos, then the service slices to `videos[:limit]`. This avoids yt-dlp flag complexity and keeps fetcher logic unchanged.
- **Optional field** — `null` / omitted means "all videos" (backwards-compatible).
- **Minimum value is 1** — API validates `limit >= 1` when provided.
- **No maximum cap** — users can set any positive integer.

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Add `limit` parameter to the service layer and CLI.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Modify** `src/service.py` — add `limit: int | None = None` param, slice videos after discovery
- **Modify** `src/cli.py` — add `--limit` / `-n` click option, slice video list

### Task 2 → Delegate to `@api-developer`

**API Developer**: Add `limit` field to the Pydantic request model and pass it through.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- **Modify** `web/api.py` — add `limit` to `FetchRequest`, validate `>= 1`, pass to service

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Add a video limit number input to the form and thread the value through the hook.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/components/FetchForm.tsx` — add number input with "All" placeholder
- **Modify** `web/frontend/src/hooks/useFetchTranscripts.ts` — add `limit` param to `startFetch()`, include in request body
- **Modify** `web/frontend/src/App.tsx` — thread `limit` through `FetchForm.onSubmit` if needed

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Task 2 (API Dev)
Task 3 (FE Dev) ──────────┘ (integration)
```

- **Task 1 and Task 3** can start in parallel
- **Task 2** depends on Task 1 (needs the service parameter)
- Integration testing requires all three

## Verification

1. **CLI**: `ytf fetch "URL" -n 3` → only 3 videos processed
2. **CLI**: `ytf fetch "URL"` (no limit) → all videos processed (unchanged)
3. **Web UI**: Set limit to 5, fetch large channel → `video_list` event shows 5 videos, only 5 processed
4. **Web UI**: Leave limit empty → all videos processed (same as today)
5. **API**: POST with `{"url":"...","limit":0}` → returns 422 validation error
6. **API**: POST with `{"url":"...","limit":2}` → SSE stream has `total: 2`
7. **API**: POST without `limit` field → all videos (backwards-compatible)
8. **Frontend**: `npm run build` passes with no errors
