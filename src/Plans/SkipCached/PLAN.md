# Skip Already-Fetched Transcripts — Development Plan

## Overview

Before calling the YouTube transcript API for each video, check the local `_index.json` for an existing entry with `has_transcript: true`. If found, skip the API call and mark the video as "cached". Videos in the index with `has_transcript: false` (metadata-only, e.g. fetched while IP was blocked) are re-fetched normally.

## Motivation

- Each transcript API call risks rate-limiting from YouTube — minimizing unnecessary calls protects the user's IP
- Re-scraping the same channel should be fast for already-fetched videos
- Only videos that genuinely need fetching should hit the YouTube API
- Videos that were previously fetched without a transcript (due to IP block, downtime, etc.) should be retried

## Architecture Change

```
Current:  for each video → always call fetch_transcript() → save all

New:      load _index.json → build cached set (has_transcript: true)
          for each video:
            if cached → load transcript body from .md file, skip API call
            if not cached → call fetch_transcript() as before
          merge with existing index entries → save all
```

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Add a transcript body extraction helper to storage.py and update service.py with cache-aware fetch logic.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Modify** `src/storage.py` — add `extract_transcript_body()` function
- **Modify** `src/service.py` — add index lookup before fetch, skip cached videos, merge index on save

### Task 2 → Delegate to `@fe-developer`

**FE Developer**: Add `"cached"` to the `VideoStep` and `transcript_source` types and update display components.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/types.ts` — add `"cached"` to `VideoStep` union, add `"cached"` to `transcript_source` union
- **Modify** `web/frontend/src/components/VideoProgressList.tsx` — add icon/label/class for `"cached"` step
- **Modify** `web/frontend/src/components/VideoTable.tsx` — handle `"cached"` in `formatTranscriptSource()`

### Task 3 → Delegate to `@api-developer`

**API Developer**: No changes needed.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

### Task 4 → Delegate to `@documentation`

**Documentation Agent**: After Tasks 1–2 are complete, update project documentation.

Full specification: [DOCUMENTATION.md](DOCUMENTATION.md)

## Dependency Graph

```
Task 1 (BE Dev) ──┐
                   ├──▶ Task 4 (Documentation)
Task 2 (FE Dev) ──┘
```

- **Task 1** (BE) and **Task 2** (FE) can run in parallel
- **Task 4** (Documentation) runs after both are complete

## Shared Contract

### New SSE Step: `"cached"`

The service emits a new `video_status` step for cached videos:

```json
{"event": "video_status", "video_id": "abc123", "step": "cached"}
```

This replaces the `checking_captions` → `captions_found` sequence for cached videos.

### Updated `transcript_source` values

| Value | Meaning |
|-------|---------|
| `"youtube"` | Freshly fetched from YouTube transcript API |
| `"cached"` | Loaded from local transcript file (skipped API call) |
| `null` | No transcript available |

### Cache Logic

A video is considered cached when ALL of these are true:
1. The video's `video_id` exists in `_index.json`
2. The entry has `has_transcript: true`
3. The referenced `.md` file exists on disk and has a non-empty transcript body

If any condition fails, the video is fetched normally.

### Index Merging

`save_transcripts()` overwrites `_index.json` with only the current batch. To preserve entries for videos not in the current batch, the service layer merges:
1. Snapshot the full original index before processing
2. After `save_transcripts()`, find entries for video IDs NOT in the current batch
3. Append them to the newly-written index and re-save

## Design Decisions

- `"cached"` is a distinct `transcript_source` — so the UI can differentiate between fresh fetches and local cache hits
- `"cached"` is a distinct `VideoStep` — so the progress list shows a unique icon/label
- The 1.5s inter-request sleep is only applied between actual API calls, not after cached lookups
- Transcript body is extracted from `.md` files by stripping everything before the first `---` separator
- Index merging preserves transcripts from previous channel fetches

## Verification

1. Fetch a channel with transcripts available → transcripts saved normally
2. Fetch **same channel** again → all cached videos show "cached" step instantly, no API calls
3. Fetch same channel with higher `limit` → cached videos skipped, new videos fetched normally
4. Videos with `has_transcript: false` are re-fetched (not treated as cached)
5. First-ever fetch (no `_index.json`) → works normally
6. UI shows distinct icon/label for cached videos in progress list
7. UI shows "📦 Cached" in transcript source column
