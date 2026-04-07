# FE Developer — Default Transcript View on Load

## Goal

Auto-load existing transcripts from the API when the app mounts, so the video table appears immediately without requiring the user to trigger a fetch.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/frontend/src/hooks/useFetchTranscripts.ts` |

## Blocked By

Task 2 (API Developer) — the `GET /api/transcripts` endpoint must exist.

## Delivers

On page load, if transcripts exist on disk, the video table and summary card appear immediately.

---

## Detailed Steps

### 1. Add `useEffect` import

**Before:**
```typescript
import { useState, useCallback } from "react";
```

**After:**
```typescript
import { useState, useCallback, useEffect } from "react";
```

### 2. Add `loadExisting()` function and `useEffect` to the hook

Add after the `startFetch` definition (before the `return` statement):

```typescript
  useEffect(() => {
    const loadExisting = async () => {
      try {
        const response = await fetch("/api/transcripts");
        if (!response.ok) return;
        const data = await response.json();
        if (data.videos.length === 0) return;

        setVideos(data.videos);
        setProgress({ current: data.total, total: data.total });
        setWithTranscript(data.with_transcript);
        setStatus("done");
      } catch {
        // Silently ignore — app starts with empty state
      }
    };

    loadExisting();
  }, []);
```

Key design decisions:
- `loadExisting` is defined inside `useEffect` — it's only used once on mount
- Empty dependency array `[]` — runs exactly once when the hook mounts
- Sets `status` to `"done"` — this triggers `SummaryCard` to render
- Sets `progress` to `{ current: total, total }` — so the progress numbers are consistent
- Does NOT set `videoProgress` — leaves it empty since there's no active fetch
- Silently ignores errors — if the API is down or no transcripts exist, the app just starts empty
- Does NOT check `status === "idle"` guard — the `useEffect` with `[]` runs before any user interaction, so status is always `"idle"` at that point
- When user later calls `startFetch`, it resets all state (including the pre-loaded data) — no conflict

### 3. No changes to `App.tsx`

The existing rendering logic already handles this correctly:
- `videos.length > 0` → renders `VideoTable` ✅
- `status === "done"` → renders `SummaryCard` ✅
- `status !== "loading"` → no `ProgressBar` or `VideoProgressList` shown ✅

---

## Expected Final State

### `useFetchTranscripts.ts` — updated hook

The hook will:
1. On mount → fetch `GET /api/transcripts` → populate state
2. On user action → `startFetch()` resets everything and runs SSE fetch as before

```typescript
export function useFetchTranscripts(): UseFetchResult {
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [progress, setProgress] = useState<FetchProgress>({ current: 0, total: 0 });
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [withTranscript, setWithTranscript] = useState(0);
  const [videoProgress, setVideoProgress] = useState<VideoProgressItem[]>([]);

  const startFetch = useCallback(async (...) => {
    // ... existing fetch logic (resets all state first)
  }, []);

  useEffect(() => {
    const loadExisting = async () => {
      try {
        const response = await fetch("/api/transcripts");
        if (!response.ok) return;
        const data = await response.json();
        if (data.videos.length === 0) return;

        setVideos(data.videos);
        setProgress({ current: data.total, total: data.total });
        setWithTranscript(data.with_transcript);
        setStatus("done");
      } catch {
        // Silently ignore
      }
    };

    loadExisting();
  }, []);

  return { videos, videoProgress, progress, status, error, withTranscript, startFetch };
}
```

---

## Verification

1. Start the API and frontend dev servers
2. Open the app fresh (with existing transcripts on disk) → table appears immediately
3. `SummaryCard` shows "X / Y videos have transcripts"
4. No progress bar or progress list visible
5. "View" button works on pre-loaded transcripts (from TranscriptViewer feature)
6. Click "Fetch" to run a new fetch → pre-loaded data is replaced, SSE streaming works normally
7. Delete `transcripts/_index.json` → reload app → empty state, no errors
8. Stop the API server → reload app → empty state, no errors in console
