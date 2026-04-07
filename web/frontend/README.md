# yt-transcript-filter — Frontend

React + TypeScript web UI for `yt-transcript-filter`. Includes transcript fetching plus an AI-powered **Topic Filter** that ranks videos by relevance using SSE updates.

## Quick Start

```bash
npm install
npm run dev
# Opens at http://localhost:5173
```

> The Vite dev server proxies `/api` requests to `http://localhost:8000` — make sure the FastAPI backend is running.

## Components

| Component | File | Description |
|-----------|------|-------------|
| **FetchForm** | `src/components/FetchForm.tsx` | URL input, video limit input, Fetch button |
| **VideoProgressList** | `src/components/VideoProgressList.tsx` | Real-time per-video step tracking during fetch (icons, labels, color-coded states, pulse animation) |
| **VideoTable** | `src/components/VideoTable.tsx` | Results table with title, duration, date, transcript source, and "View" button |
| **TranscriptModal** | `src/components/TranscriptModal.tsx` | Full-screen modal overlay to read transcript content (fetched from API) |
| **ProgressBar** | `src/components/ProgressBar.tsx` | Visual progress bar with "X / Y videos processed" |
| **SummaryCard** | `src/components/SummaryCard.tsx` | Completion banner showing transcript count |
| **TopicFilterPanel** | `src/components/TopicFilterPanel.tsx` | Topic text input + threshold slider + Filter action |
| **FilterResultsList** | `src/components/FilterResultsList.tsx` | Ranked relevance results with score styling and AI explanations |
| **ErrorMessage** | `src/components/ErrorMessage.tsx` | Red alert box for error display |

## Hooks

### `useFetchTranscripts`

`src/hooks/useFetchTranscripts.ts`:

1. Auto-loads saved transcript rows on mount via `GET /api/transcripts`
2. Sends a `POST /api/fetch-transcripts` request with `url`, `lang`, and `limit`
3. Sets `status = "done"` when preloaded data exists so summary/table render immediately
4. Reads the SSE stream via `ReadableStream`
5. Handles 5 event types: `video_list`, `video_status`, `progress`, `done`, `error`
6. Returns reactive state: `videos`, `videoProgress`, `progress`, `status`, `error`, `withTranscript`, `startFetch()`

### `useTopicFilter`

`src/hooks/useTopicFilter.ts`:

1. Sends `POST /api/filter-by-topic` with `topic` and `threshold`
2. Streams filter SSE events via `ReadableStream`
3. Tracks filter status/progress (`filter_start`, `filter_progress`, `filter_done`, `filter_error`)
4. Accumulates per-video relevance results and `relevantCount`
5. Exposes `startFilter()` and `resetFilter()` for App-level integration

## Component Tree

```
App
├── FetchForm              (url + limit inputs + fetch button)
├── ErrorMessage           (conditional: error state)
├── ProgressBar            (conditional: loading state)
│   └── VideoProgressList  (conditional: loading + videoProgress available)
├── SummaryCard            (conditional: done state — transcript count)
├── VideoTable             (conditional: videos.length > 0 — with "View" button per row)
│   └── "View" button      (per row, if has_transcript — opens TranscriptModal)
├── TopicFilterPanel       (conditional: fetch done + transcripts available)
├── ProgressBar            (conditional: topic filtering in progress)
├── ErrorMessage           (conditional: topic filter error)
├── FilterResultsList      (conditional: topic filter done + results)
└── TranscriptModal        (conditional: selectedVideo !== null — fetches GET /api/transcripts/{id})
```

## Build

```bash
npm run build    # Production build → dist/
npm run preview  # Preview production build locally
```

## Tech Stack

- **Vite** — build tool with HMR
- **React 19** + **TypeScript**
- No external UI libraries — plain HTML + CSS
