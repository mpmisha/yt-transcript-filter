# FE Developer — React + TypeScript App

## Goal

Build the complete frontend: scaffold a Vite + React + TypeScript project, create all UI components, implement SSE integration via a custom hook, and wire everything together. Start with mock data so all components can be developed and tested independently of the backend.

## Files

| Action | Path |
|--------|------|
| **Create** | `web/frontend/` — entire Vite project |
| Key files | `src/App.tsx`, `src/types.ts` |
| Components | `src/components/FetchForm.tsx`, `VideoTable.tsx`, `ProgressBar.tsx`, `SummaryCard.tsx`, `ErrorMessage.tsx` |
| Hook | `src/hooks/useFetchTranscripts.ts` |
| Config | `vite.config.ts` (proxy setup) |

## Blocked By

Nothing for steps 1–7 (all UI work uses mock data). Steps 8–9 (real integration) blocked by **API Developer**.

## Delivers

Complete working frontend that progressively displays fetched videos via SSE.

---

## Detailed Steps

### 1. Scaffold the Project

```bash
cd web
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

### 2. Configure Vite Proxy

In `vite.config.ts`, add a proxy so `/api` requests are forwarded to the FastAPI backend during development:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

### 3. Define Shared Types

Create `src/types.ts`:

```typescript
export interface VideoInfo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  upload_date: string | null;
  has_transcript: boolean;
}

export interface FetchProgress {
  current: number;
  total: number;
}

export type FetchStatus = "idle" | "loading" | "done" | "error";

export interface SSEProgressEvent {
  event: "progress";
  current: number;
  total: number;
  video_id: string;
  title: string;
  duration: number | null;
  upload_date: string | null;
  url: string;
  has_transcript: boolean;
}

export interface SSEDoneEvent {
  event: "done";
  total: number;
  with_transcript: number;
  output_dir: string;
}

export interface SSEErrorEvent {
  event: "error";
  detail: string;
}

export type SSEEvent = SSEProgressEvent | SSEDoneEvent | SSEErrorEvent;
```

### 4. Build Components

#### `src/components/FetchForm.tsx`

- **Props**: `onSubmit(url: string, lang: string)`, `disabled: boolean`
- **UI**:
  - Text input for YouTube URL (placeholder: `"https://www.youtube.com/@ChannelName/videos"`)
  - Text input for language (default: `"en"`, small width)
  - "Fetch" button
- **Behavior**:
  - Button disabled when `disabled` prop is true (while loading)
  - Submit on button click or Enter key
  - Basic client-side validation: URL must not be empty

#### `src/components/VideoTable.tsx`

- **Props**: `videos: VideoInfo[]`
- **Columns**:

| Column | Content | Notes |
|--------|---------|-------|
| # | Row number | Right-aligned |
| Title | Video title | Links to YouTube URL (`target="_blank"`) |
| Duration | Formatted as `mm:ss` | Handle `null` → show `"—"` |
| Upload Date | Formatted as `YYYY-MM-DD` | Parse from `"YYYYMMDD"` string. Handle `null` → `"—"` |
| Transcript | ✅ or ❌ | Based on `has_transcript` |

- **Behavior**: Rows appear progressively (new videos appended as SSE events arrive)

#### `src/components/ProgressBar.tsx`

- **Props**: `current: number`, `total: number`
- **UI**: HTML progress bar + text label `"3 / 10 videos processed"`
- **Behavior**: Only visible when `total > 0`. Percentage = `(current / total) * 100`

#### `src/components/SummaryCard.tsx`

- **Props**: `total: number`, `withTranscript: number`
- **UI**: Card/banner showing `"✅ 8 / 10 videos have transcripts"`
- **Behavior**: Only visible when status is `"done"`

#### `src/components/ErrorMessage.tsx`

- **Props**: `message: string | null`
- **UI**: Red alert box with error text
- **Behavior**: Only renders when `message` is not null

### 5. Build the SSE Hook

Create `src/hooks/useFetchTranscripts.ts`:

```typescript
import { useState, useCallback, useRef } from "react";
import type { VideoInfo, FetchProgress, FetchStatus, SSEEvent } from "../types";

interface UseFetchResult {
  videos: VideoInfo[];
  progress: FetchProgress;
  status: FetchStatus;
  error: string | null;
  withTranscript: number;
  startFetch: (url: string, lang: string) => void;
}

export function useFetchTranscripts(): UseFetchResult {
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [progress, setProgress] = useState<FetchProgress>({ current: 0, total: 0 });
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [withTranscript, setWithTranscript] = useState(0);

  const startFetch = useCallback(async (url: string, lang: string) => {
    // Reset state
    setVideos([]);
    setProgress({ current: 0, total: 0 });
    setStatus("loading");
    setError(null);
    setWithTranscript(0);

    try {
      const response = await fetch("/api/fetch-transcripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, lang }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data: SSEEvent = JSON.parse(line.slice(6));

          if (data.event === "progress") {
            setVideos((prev) => [...prev, {
              video_id: data.video_id,
              title: data.title,
              url: data.url,
              duration: data.duration,
              upload_date: data.upload_date,
              has_transcript: data.has_transcript,
            }]);
            setProgress({ current: data.current, total: data.total });
          } else if (data.event === "done") {
            setWithTranscript(data.with_transcript);
            setStatus("done");
          } else if (data.event === "error") {
            setError(data.detail);
            setStatus("error");
          }
        }
      }

      // If stream ended without a done event, mark as done
      setStatus((prev) => (prev === "loading" ? "done" : prev));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("error");
    }
  }, []);

  return { videos, progress, status, error, withTranscript, startFetch };
}
```

### 6. Wire Everything in `App.tsx`

```typescript
import { FetchForm } from "./components/FetchForm";
import { VideoTable } from "./components/VideoTable";
import { ProgressBar } from "./components/ProgressBar";
import { SummaryCard } from "./components/SummaryCard";
import { ErrorMessage } from "./components/ErrorMessage";
import { useFetchTranscripts } from "./hooks/useFetchTranscripts";

function App() {
  const { videos, progress, status, error, withTranscript, startFetch } = useFetchTranscripts();

  return (
    <div>
      <h1>YouTube Transcript Fetcher</h1>
      <FetchForm onSubmit={startFetch} disabled={status === "loading"} />
      <ErrorMessage message={error} />
      {status === "loading" && <ProgressBar current={progress.current} total={progress.total} />}
      {status === "done" && <SummaryCard total={progress.total} withTranscript={withTranscript} />}
      {videos.length > 0 && <VideoTable videos={videos} />}
    </div>
  );
}
```

### 7. Mock Data for Early Development

Before the API is ready, use hardcoded mock data in `App.tsx` to develop and test all components visually:

```typescript
const MOCK_VIDEOS: VideoInfo[] = [
  { video_id: "abc123", title: "Introduction to TypeScript", url: "https://youtube.com/watch?v=abc123", duration: 600, upload_date: "20240115", has_transcript: true },
  { video_id: "def456", title: "React Hooks Deep Dive", url: "https://youtube.com/watch?v=def456", duration: 1200, upload_date: "20240220", has_transcript: true },
  { video_id: "ghi789", title: "Live Q&A Session", url: "https://youtube.com/watch?v=ghi789", duration: 3600, upload_date: "20240310", has_transcript: false },
];
```

### 8. Integrate with Real API

Once the API Developer delivers:

1. Remove mock data
2. Ensure Vite proxy is working (`/api` → `localhost:8000`)
3. Test with a real playlist URL

### 9. End-to-End Verification

1. Start backend: `uvicorn web.api:app --reload`
2. Start frontend: `cd web/frontend && npm run dev`
3. Enter a small playlist URL, click Fetch
4. **Verify**: progress bar advances as each video is processed
5. **Verify**: table rows appear one by one
6. **Verify**: summary card shows correct count when done
7. **Verify**: videos without transcripts show ❌
8. **Verify**: invalid URL shows error message
9. **Verify**: Fetch button is disabled while loading

---

## Utility Functions

### Duration Formatter

```typescript
export function formatDuration(seconds: number | null): string {
  if (seconds == null) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
```

### Date Formatter

```typescript
export function formatDate(dateStr: string | null): string {
  if (!dateStr || dateStr.length !== 8) return "—";
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
}
```

---

## Component Tree

```
App
├── FetchForm          (url input, lang input, fetch button)
├── ErrorMessage       (conditional: error state)
├── ProgressBar        (conditional: loading state)
├── SummaryCard        (conditional: done state)
└── VideoTable         (conditional: videos.length > 0)
    └── VideoRow × N   (one per video)
```

---

## Definition of Done

- [ ] Vite + React + TypeScript project scaffolded in `web/frontend/`
- [ ] Vite proxy configured for `/api` → `localhost:8000`
- [ ] All 5 components render correctly with mock data
- [ ] `useFetchTranscripts` hook parses SSE stream and updates state
- [ ] `App.tsx` wires form → hook → components
- [ ] Progress bar shows during loading, hides when done
- [ ] Summary card appears when fetch completes
- [ ] Error messages display for invalid URLs / network errors
- [ ] Fetch button is disabled during loading
- [ ] Duration displayed as `mm:ss`, dates as `YYYY-MM-DD`
- [ ] End-to-end test with a real playlist works correctly
