# Single Video URL Support — Development Plan

## Overview

Allow users to paste a single YouTube video URL (e.g. `https://www.youtube.com/watch?v=VIDEO_ID` or `https://youtu.be/VIDEO_ID`) in the same fetch input field. The backend detects it's a single video and processes it through the same transcript pipeline. No UI changes.

## Motivation

- Users may want to fetch a transcript for just one video without needing a channel/playlist URL
- The fetch input currently only works reliably with channel/playlist URLs

## Analysis

`yt-dlp --flat-playlist --dump-json` already handles single video URLs transparently — it returns one JSON line with the video's metadata, treating it as a "playlist of 1". This means `get_video_list()` in `src/fetcher.py` should already work for single video URLs without code changes.

**However**, `--flat-playlist` may return incomplete metadata for single videos (e.g. missing `title`, `duration`, `upload_date`) because it's optimized to skip per-video page fetches for playlists. This needs verification.

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Verify yt-dlp handles single video URLs correctly. If `--flat-playlist` returns incomplete metadata for single videos, add detection logic to call yt-dlp without `--flat-playlist` for single video URLs.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Modify** `src/fetcher.py` — add `_is_single_video_url()` helper, update `get_video_list()` to skip `--flat-playlist` for single videos if needed

### Task 2 → Delegate to `@fe-developer`

**FE Developer**: No changes needed.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

### Task 3 → Delegate to `@api-developer`

**API Developer**: No changes needed.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Verification
```

Only the BE task may require changes. FE and API are passthrough.

## Shared Contract

No changes to SSE events, types, or API endpoints. A single video URL produces the same event sequence as a channel with one video:

```
video_list (total: 1) → video_status → progress → done
```

## Design Decisions

- Detection uses URL parsing (look for `watch?v=` or `youtu.be/` patterns) rather than calling yt-dlp twice
- No UI changes — the input field accepts any YouTube URL
- The service layer (`src/service.py`) is completely unaware of single vs multi — it just processes whatever `get_video_list()` returns
- If `--flat-playlist` already returns full metadata for single videos, no code changes are needed at all

## Verification

1. Paste a single video URL → one video appears in progress list, transcript fetched normally
2. Paste a `youtu.be/` short URL → same behavior
3. Paste a channel URL → works as before (no regression)
4. Paste a playlist URL → works as before
5. Paste a `watch?v=...&list=...` URL → fetches only the single video, not the whole playlist
