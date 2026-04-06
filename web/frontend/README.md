# yt-transcript-filter — Frontend

React + TypeScript web UI for the YouTube Transcript Fetcher. Provides a **Fetch Panel** where users enter a YouTube channel/playlist URL, optionally enable Whisper auto-transcription, set a video limit, and see results populate progressively via Server-Sent Events.

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
| **FetchForm** | `src/components/FetchForm.tsx` | URL input, language input, video limit input, Whisper toggle + model dropdown, Fetch button |
| **VideoProgressList** | `src/components/VideoProgressList.tsx` | Real-time per-video step tracking during fetch (icons, labels, color-coded states, pulse animation) |
| **VideoTable** | `src/components/VideoTable.tsx` | Results table with title, duration, date, and transcript source (YouTube / Whisper / None) |
| **ProgressBar** | `src/components/ProgressBar.tsx` | Visual progress bar with "X / Y videos processed" |
| **SummaryCard** | `src/components/SummaryCard.tsx` | Completion banner showing transcript count + Whisper count |
| **ErrorMessage** | `src/components/ErrorMessage.tsx` | Red alert box for error display |

## SSE Hook

`src/hooks/useFetchTranscripts.ts` — custom React hook that:

1. Sends a `POST /api/fetch-transcripts` request with `url`, `lang`, `whisper_model`, and `limit`
2. Reads the SSE stream via `ReadableStream`
3. Handles 5 event types: `video_list`, `video_status`, `progress`, `done`, `error`
4. Returns reactive state: `videos`, `videoProgress`, `progress`, `status`, `error`, `withTranscript`, `withWhisper`, `startFetch()`

## Component Tree

```
App
├── FetchForm              (url, lang, limit inputs + Whisper toggle/dropdown + fetch button)
├── ErrorMessage           (conditional: error state)
├── ProgressBar            (conditional: loading state)
│   └── VideoProgressList  (conditional: loading + videoProgress available)
├── SummaryCard            (conditional: done state — transcript + Whisper counts)
└── VideoTable             (conditional: videos.length > 0 — with transcript source column)
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
