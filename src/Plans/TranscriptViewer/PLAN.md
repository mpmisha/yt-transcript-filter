# Transcript Viewer — Development Plan

## Overview

Add a "View Transcript" button in the video table for videos that have transcripts. Clicking the button opens a modal overlay that fetches and displays the full formatted transcript from a new API endpoint.

## Motivation

- Transcripts are saved as formatted Markdown files but can only be viewed by opening the file on disk
- Users need a way to read transcripts without leaving the UI
- The modal approach keeps the SPA feel — no routing needed

## Architecture Change

```
Current:  transcripts saved to disk → user opens file manually
New:      transcripts saved to disk → API endpoint serves content → modal displays it
```

New data flow:
```
VideoTable "View" button → App state (selectedVideo) → TranscriptModal mounts
  → GET /api/transcripts/{video_id} → API reads from disk via load_index() + load_transcript()
  → JSON { video_id, title, content } → modal renders content
```

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: No changes needed.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

### Task 2 → Delegate to `@api-developer`

**API Developer**: Add a GET endpoint to serve transcript content by video ID.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- **Modify** `web/api.py` — add `GET /api/transcripts/{video_id}` endpoint

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Create the transcript modal component, add a "View" button to the video table, and wire up state in App.tsx.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Create** `web/frontend/src/components/TranscriptModal.tsx`
- **Modify** `web/frontend/src/components/VideoTable.tsx` — add "View" button column + callback prop
- **Modify** `web/frontend/src/App.tsx` — add selectedVideo state, render modal

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

**`GET /api/transcripts/{video_id}`**

Success response (200):
```json
{
  "video_id": "rGLXc1GmsaI",
  "title": "This App Makes $35K/Month With One Influencer",
  "content": "# This App Makes $35K/Month With One Influencer\n\n**Video:** https://..."
}
```

Not found response (404):
```json
{
  "detail": "Transcript not found"
}
```

### Frontend State

```typescript
// In App.tsx
selectedVideo: { videoId: string; title: string } | null
```

### TranscriptModal Props

```typescript
interface TranscriptModalProps {
  videoId: string;
  title: string;
  onClose: () => void;
}
```

### VideoTable Props (updated)

```typescript
interface VideoTableProps {
  videos: VideoInfo[];
  onViewTranscript: (videoId: string, title: string) => void;
}
```

## Design Decisions

- **Plain text rendering** — transcript content rendered with preserved whitespace, not parsed as Markdown/HTML. Avoids XSS risk and the `.md` format is already human-readable
- **Modal** — not a separate page. No routing needed, keeps SPA feel
- **No caching** — transcripts are small, re-fetch on each open is acceptable
- **API returns raw file content** — frontend displays as-is, no re-formatting needed

## Verification

1. `curl http://localhost:8000/api/transcripts/rGLXc1GmsaI` → JSON with transcript content
2. `curl http://localhost:8000/api/transcripts/nonexistent` → 404
3. Fetch a channel in the UI → "View" button appears for videos with transcripts
4. Click "View" → modal opens with formatted transcript content
5. Close via X button / Escape key / click outside → modal closes
6. Videos without transcripts show no "View" button
