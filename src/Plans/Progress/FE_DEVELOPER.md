# FE Developer — Detailed Progress Panel

## Goal

Show real-time per-video step tracking during fetch. Instead of only showing completed videos, the UI should display all videos immediately (from the `video_list` event) and update each video's status as `video_status` events arrive. After completion, the progress list is replaced by the existing `VideoTable` + `SummaryCard`.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/frontend/src/types.ts` — add new types for progress events |
| **Modify** | `web/frontend/src/hooks/useFetchTranscripts.ts` — handle new SSE events |
| **Create** | `web/frontend/src/components/VideoProgressList.tsx` — per-video progress list |
| **Modify** | `web/frontend/src/App.tsx` — integrate `VideoProgressList` into layout |

## Blocked By

Nothing — can start immediately. Build the UI with mock data first; integration with real SSE events works once BE Developer ships.

## Delivers

A real-time progress panel that shows all videos with per-step status updates during fetching.

---

## Step 1: Add types to `types.ts`

### New types to add

```ts
export type VideoStep =
  | "pending"
  | "checking_captions"
  | "captions_found"
  | "no_captions"
  | "downloading_audio"
  | "transcribing"
  | "whisper_complete"
  | "whisper_failed"
  | "skipped";

export interface SSEVideoListEvent {
  event: "video_list";
  total: number;
  videos: Array<{
    video_id: string;
    title: string;
    duration: number | null;
    upload_date: string | null;
    url: string;
  }>;
}

export interface SSEVideoStatusEvent {
  event: "video_status";
  video_id: string;
  step: VideoStep;
}

export interface VideoProgressItem {
  video_id: string;
  title: string;
  duration: number | null;
  upload_date: string | null;
  url: string;
  step: VideoStep;
}
```

### Update `SSEEvent` union

Change:
```ts
export type SSEEvent = SSEProgressEvent | SSEDoneEvent | SSEErrorEvent;
```

To:
```ts
export type SSEEvent =
  | SSEVideoListEvent
  | SSEVideoStatusEvent
  | SSEProgressEvent
  | SSEDoneEvent
  | SSEErrorEvent;
```

---

## Step 2: Update `useFetchTranscripts.ts` hook

### New state to add

```ts
const [videoProgress, setVideoProgress] = useState<VideoProgressItem[]>([]);
```

### Reset on new fetch

In `startFetch`, add to the existing reset block:
```ts
setVideoProgress([]);
```

### Handle new events in the SSE reader

Add these cases to the existing event handler:

```ts
if (data.event === "video_list") {
  setVideoProgress(
    data.videos.map((v) => ({
      video_id: v.video_id,
      title: v.title,
      duration: v.duration,
      upload_date: v.upload_date,
      url: v.url,
      step: "pending" as const,
    }))
  );
  setProgress({ current: 0, total: data.total });
} else if (data.event === "video_status") {
  setVideoProgress((prev) =>
    prev.map((item) =>
      item.video_id === data.video_id
        ? { ...item, step: data.step }
        : item
    )
  );
} else if (data.event === "progress") {
  // existing progress handling stays the same
}
```

### Updated return type

Add `videoProgress` to the hook's return interface and return value:

```ts
interface UseFetchResult {
  videos: VideoInfo[];
  videoProgress: VideoProgressItem[];
  progress: FetchProgress;
  status: FetchStatus;
  error: string | null;
  withTranscript: number;
  withWhisper: number;
  startFetch: (url: string, lang: string, whisperModel?: WhisperModel | null) => void;
}
```

Return:
```ts
return { videos, videoProgress, progress, status, error, withTranscript, withWhisper, startFetch };
```

---

## Step 3: Create `VideoProgressList.tsx`

Create `web/frontend/src/components/VideoProgressList.tsx`.

### Props

```ts
import type { VideoProgressItem } from "../types";

interface VideoProgressListProps {
  items: VideoProgressItem[];
}
```

### Component

```tsx
export const VideoProgressList = ({ items }: VideoProgressListProps) => {
  return (
    <div className="video-progress-list">
      {items.map((item) => (
        <div
          key={item.video_id}
          className={`video-progress-item ${getStepClass(item.step)}`}
        >
          <span className="video-progress-icon">{getStepIcon(item.step)}</span>
          <span className="video-progress-title">{item.title}</span>
          <span className="video-progress-step">{getStepLabel(item.step)}</span>
        </div>
      ))}
    </div>
  );
};
```

### Helper functions (in the same file, above the component)

```ts
const getStepIcon = (step: VideoStep): string => {
  switch (step) {
    case "pending":
      return "⬜";
    case "checking_captions":
    case "downloading_audio":
    case "transcribing":
      return "⏳";
    case "captions_found":
      return "✅";
    case "no_captions":
      return "⚠️";
    case "whisper_complete":
      return "🎤";
    case "whisper_failed":
      return "❌";
    case "skipped":
      return "⏭️";
  }
};

const getStepLabel = (step: VideoStep): string => {
  switch (step) {
    case "pending":
      return "Pending";
    case "checking_captions":
      return "Checking captions…";
    case "captions_found":
      return "YouTube captions";
    case "no_captions":
      return "No captions found";
    case "downloading_audio":
      return "Downloading audio…";
    case "transcribing":
      return "Transcribing…";
    case "whisper_complete":
      return "Whisper (complete)";
    case "whisper_failed":
      return "Whisper (failed)";
    case "skipped":
      return "Skipped";
  }
};

const getStepClass = (step: VideoStep): string => {
  switch (step) {
    case "pending":
      return "step-pending";
    case "checking_captions":
    case "downloading_audio":
    case "transcribing":
      return "step-active";
    case "captions_found":
    case "whisper_complete":
      return "step-success";
    case "no_captions":
      return "step-warning";
    case "whisper_failed":
      return "step-error";
    case "skipped":
      return "step-skipped";
  }
};
```

### Styling

Add CSS to `App.css` (following existing project style):

```css
.video-progress-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin: 16px 0;
  max-height: 400px;
  overflow-y: auto;
}

.video-progress-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  transition: background 0.2s, border-color 0.2s;
}

.video-progress-icon {
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.video-progress-title {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.video-progress-step {
  flex-shrink: 0;
  font-size: 0.8rem;
  color: #6c757d;
}

/* Step state styles */
.step-active {
  background: #fff3cd;
  border-color: #ffc107;
}

.step-success {
  background: #d4edda;
  border-color: #28a745;
}

.step-warning {
  background: #fff3cd;
  border-color: #e0a800;
}

.step-error {
  background: #f8d7da;
  border-color: #dc3545;
}

.step-skipped {
  background: #e9ecef;
  border-color: #ced4da;
  opacity: 0.7;
}

.step-pending {
  opacity: 0.5;
}

/* Animate active items */
.step-active .video-progress-step {
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

---

## Step 4: Update `App.tsx`

### Add import

```tsx
import { VideoProgressList } from "./components/VideoProgressList";
```

### Destructure `videoProgress` from hook

```tsx
const { videos, videoProgress, progress, status, error, withTranscript, withWhisper, startFetch } =
  useFetchTranscripts();
```

### Updated JSX layout

```tsx
return (
  <div className="app">
    <h1>YouTube Transcript Fetcher</h1>
    <FetchForm onSubmit={startFetch} disabled={status === "loading"} />
    <ErrorMessage message={error} />
    {status === "loading" && (
      <>
        <ProgressBar current={progress.current} total={progress.total} />
        {videoProgress.length > 0 && (
          <VideoProgressList items={videoProgress} />
        )}
      </>
    )}
    {status === "done" && (
      <SummaryCard total={progress.total} withTranscript={withTranscript} withWhisper={withWhisper} />
    )}
    {videos.length > 0 && <VideoTable videos={videos} />}
  </div>
);
```

**Key behavior**:
- While `status === "loading"`: show `ProgressBar` + `VideoProgressList`
- When `status === "done"`: `VideoProgressList` disappears, `SummaryCard` + `VideoTable` appear (same as today)

---

## UI Mockup (during loading)

```
┌─────────────────────────────────────────────────────────┐
│  YouTube Transcript Fetcher                             │
│  [URL input] [Lang] [Whisper toggle] [Fetch]            │
├─────────────────────────────────────────────────────────┤
│  ████████░░░░░░░░░  3 / 15 videos                      │
├─────────────────────────────────────────────────────────┤
│  ✅  Intro to Python            YouTube captions         │
│  🎤  Advanced React              Whisper (complete)      │
│  ⏳  Live Q&A                    Transcribing…           │
│  ⬜  State Management            Pending                 │
│  ⬜  Testing Basics              Pending                 │
│  ⬜  Deploy Guide                Pending                 │
│  ...                                                     │
└─────────────────────────────────────────────────────────┘
```

---

## Edge Cases

1. **Empty channel** — `video_list` has `total: 0` and empty array. Show "No videos found" or simply no progress list.
2. **Single video** — progress list has one item. Works normally.
3. **Long titles** — use `text-overflow: ellipsis` (already in CSS above).
4. **Many videos (100+)** — the `max-height: 400px` + `overflow-y: auto` creates a scrollable list.
5. **Error during fetch** — if `error` event arrives, the loading state switches to error. `VideoProgressList` disappears because `status !== "loading"`.

---

## Verification

1. Fetch a channel → `VideoProgressList` appears immediately with all videos as "Pending"
2. Videos update one by one to "Checking captions…" → "YouTube captions" (green)
3. With Whisper enabled: videos without captions show "Downloading audio…" → "Transcribing…" → "Whisper (complete)" (with pulse animation on active steps)
4. Progress bar advances as each video completes
5. After `done` event: `VideoProgressList` disappears, `SummaryCard` + `VideoTable` appear
6. Active steps have a pulsing animation on the step label
7. Scroll works when there are many videos

## Definition of Done

- [ ] `VideoStep` type added to `types.ts`
- [ ] `SSEVideoListEvent` and `SSEVideoStatusEvent` added to `types.ts`
- [ ] `VideoProgressItem` interface added to `types.ts`
- [ ] `SSEEvent` union updated to include new events
- [ ] `useFetchTranscripts` hook handles `video_list` events (populates all videos as pending)
- [ ] `useFetchTranscripts` hook handles `video_status` events (updates per-video step)
- [ ] `videoProgress` state exposed from hook
- [ ] `VideoProgressList` component created with step icons, labels, and CSS classes
- [ ] CSS styles added for progress list (step-active, step-success, step-error, pulse animation)
- [ ] `App.tsx` shows `VideoProgressList` during loading phase
- [ ] `VideoProgressList` disappears when status changes to done
- [ ] No TypeScript errors (`npm run build` passes)
