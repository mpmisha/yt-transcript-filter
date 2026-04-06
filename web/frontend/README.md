# yt-transcript-filter — Frontend

React + TypeScript web UI for the YouTube Transcript Fetcher. Provides a **Fetch Panel** where users enter a YouTube channel/playlist URL and see results populate progressively via Server-Sent Events.

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
| **FetchForm** | `src/components/FetchForm.tsx` | URL + language input with Fetch button |
| **VideoTable** | `src/components/VideoTable.tsx` | Progressive results table (title, duration, date, transcript status) |
| **ProgressBar** | `src/components/ProgressBar.tsx` | Visual progress bar with "X / Y videos processed" |
| **SummaryCard** | `src/components/SummaryCard.tsx` | Completion banner showing transcript count |
| **ErrorMessage** | `src/components/ErrorMessage.tsx` | Red alert box for error display |

## SSE Hook

`src/hooks/useFetchTranscripts.ts` — custom React hook that:

1. Sends a `POST /api/fetch-transcripts` request
2. Reads the SSE stream via `ReadableStream`
3. Parses `progress`, `done`, and `error` events
4. Returns reactive state: `videos`, `progress`, `status`, `error`, `withTranscript`, `startFetch()`

## Component Tree

```
App
├── FetchForm          (url input, lang input, fetch button)
├── ErrorMessage       (conditional: error state)
├── ProgressBar        (conditional: loading state)
├── SummaryCard        (conditional: done state)
└── VideoTable         (conditional: videos.length > 0)
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
