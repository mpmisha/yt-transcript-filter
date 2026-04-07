# Skip Reason Messages + Rate-Limit Short-Circuit — Development Plan

## Overview

When a transcript cannot be fetched, the UI currently shows a generic "Skipped" label with no explanation. This feature adds structured skip reasons so the user sees _why_ each video was skipped (e.g. "Transcripts disabled by uploader", "YouTube rate limit"). Additionally, when YouTube rate-limits one request (`IpBlocked` / `RequestBlocked`), all remaining uncached videos are auto-skipped immediately instead of hitting the same wall repeatedly.

## Motivation

- Users see "Skipped" with no way to know if the problem is temporary (rate limit) or permanent (transcripts disabled)
- Rate-limiting from YouTube affects all subsequent requests from the same IP — retrying wastes time and compounds the block
- The `error` field already exists on `SSEVideoStatusEvent` and `VideoProgressItem` but is never populated

## Architecture Change

```
Current:  fetch_transcript() returns str | None
          service.py emits {"step": "skipped"} with no reason

New:      fetch_transcript() returns (str | None, str | None) — (text, skip_reason)
          service.py reads skip_reason → includes it as "error" in skipped event
          service.py checks if reason is rate-limit → flag → auto-skips remaining uncached videos
```

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Change `fetch_transcript()` return type to a tuple with a reason string. Update service.py to propagate the reason and add rate-limit short-circuit logic.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Modify** `src/fetcher.py` — change `fetch_transcript()` return type, update `fetch_all_transcripts()`
- **Modify** `src/service.py` — unpack tuple, attach reason to `"skipped"` events, add rate-limit short-circuit

### Task 2 → Delegate to `@fe-developer`

**FE Developer**: Update the `VideoProgressList` component to display the skip reason alongside the "Skipped" label.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/components/VideoProgressList.tsx` — show reason text when `error` is present on skipped items

### Task 3 → Delegate to `@api-developer`

**API Developer**: No changes needed.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

## Dependency Graph

```
Task 1 (BE Dev) ──┐
                   ├──▶ Integration testing
Task 2 (FE Dev) ──┘
```

- **Task 1** (BE) and **Task 2** (FE) can run in parallel
- Integration testing runs after both are complete

## Shared Contract

### Skip Reason in `video_status` Event

The `"skipped"` status event now includes an `error` field with a human-readable reason:

```json
{"event": "video_status", "video_id": "abc123", "step": "skipped", "error": "Transcripts disabled by uploader"}
```

### Reason Strings

| Exception | `error` field value |
|-----------|---------------------|
| `NoTranscriptFound` | `"No transcript available"` |
| `TranscriptsDisabled` | `"Transcripts disabled by uploader"` |
| `VideoUnavailable` | `"Video unavailable"` |
| `IpBlocked` | `"YouTube rate limit (IP blocked)"` |
| `RequestBlocked` | `"YouTube rate limit (request blocked)"` |
| Generic `Exception` | `"Unexpected error: {exc}"` |
| Rate-limit short-circuit | `"Skipped — YouTube rate limited a previous request"` |

### Rate-Limit Detection

A reason string starting with `"YouTube rate limit"` triggers the short-circuit flag. All subsequent uncached videos are auto-skipped with the short-circuit reason.

## Design Decisions

- `fetch_transcript()` returns a tuple `(str | None, str | None)` rather than raising custom exceptions — minimal contract change, backward compatible with callers that destructure
- Rate-limit detection uses string prefix matching (`reason.startswith("YouTube rate limit")`) — simple, no new enums needed
- The `"no_captions"` → `"skipped"` two-step emission is preserved; the reason is attached only to the `"skipped"` event
- No new SSE event types or `VideoStep` values needed — the existing `error` field carries the reason
- `fetch_all_transcripts()` (used by CLI) is also updated for the new return type

## Verification

1. Fetch a channel where some videos have transcripts disabled → skipped videos show "Transcripts disabled by uploader" in UI
2. Fetch a channel where no transcript exists → shows "No transcript available"
3. Simulate rate limit (temporarily raise `IpBlocked` in `fetch_transcript()` on 2nd uncached video) → video 2 shows "YouTube rate limit (IP blocked)", videos 3+ show "Skipped — YouTube rate limited a previous request" without delay
4. Cached videos are unaffected by rate-limit short-circuit — they still load from disk
5. `npx tsc --noEmit` passes without errors
6. Existing tests still pass
