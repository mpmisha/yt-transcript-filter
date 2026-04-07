# FE Developer — Transcript Viewer

## Goal

Add a "View" button in the video table and a modal overlay to display transcript content fetched from the API.

## Files

| Action | File |
|--------|------|
| **Create** | `web/frontend/src/components/TranscriptModal.tsx` |
| **Modify** | `web/frontend/src/components/VideoTable.tsx` |
| **Modify** | `web/frontend/src/App.tsx` |

## Blocked By

Task 2 (API Developer) — the `GET /api/transcripts/{video_id}` endpoint must exist before the modal can fetch content.

## Delivers

A clickable "View" button in the video table that opens a modal overlay displaying the full formatted transcript.

---

## Detailed Steps

### 1. Create `TranscriptModal.tsx`

Create `web/frontend/src/components/TranscriptModal.tsx`:

```tsx
import { useState, useEffect, useCallback } from "react";

interface TranscriptModalProps {
  videoId: string;
  title: string;
  onClose: () => void;
}

export const TranscriptModal = ({ videoId, title, onClose }: TranscriptModalProps) => {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTranscript = async () => {
      try {
        const response = await fetch(`/api/transcripts/${videoId}`);
        if (!response.ok) {
          throw new Error("Failed to load transcript");
        }
        const data = await response.json();
        setContent(data.content);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };
    fetchTranscript();
  }, [videoId]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="transcript-modal-overlay" onClick={handleOverlayClick}>
      <div className="transcript-modal">
        <div className="transcript-modal-header">
          <h2>{title}</h2>
          <button className="transcript-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="transcript-modal-body">
          {loading && <p>Loading transcript…</p>}
          {error && <p className="transcript-modal-error">Error: {error}</p>}
          {content && <pre className="transcript-content">{content}</pre>}
        </div>
      </div>
    </div>
  );
};
```

Key design decisions:
- Named export `TranscriptModal` (per project conventions)
- Props interface `TranscriptModalProps` follows `{Component}Props` naming convention
- Fetches from `GET /api/transcripts/{videoId}` on mount
- Three states: loading, error, content
- Close on: X button click, Escape key, click outside (overlay click where target === currentTarget)
- Content rendered in `<pre>` to preserve whitespace/line breaks from the `.md` file
- No Markdown-to-HTML parsing — avoids XSS and the formatted `.md` is already readable

### 2. Add styles for the modal

Add these styles to `web/frontend/src/App.css` (at the end):

```css
.transcript-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.transcript-modal {
  background: white;
  border-radius: 8px;
  width: 90%;
  max-width: 800px;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.3);
}

.transcript-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.transcript-modal-header h2 {
  margin: 0;
  font-size: 1.1rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.transcript-modal-close {
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  color: #6b7280;
}

.transcript-modal-close:hover {
  background: #f3f4f6;
  color: #111827;
}

.transcript-modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.transcript-content {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.6;
  margin: 0;
}

.transcript-modal-error {
  color: #dc2626;
}
```

### 3. Modify `VideoTable.tsx` — add "View" button column

#### 3a. Update the props interface

**Before:**
```tsx
interface VideoTableProps {
  videos: VideoInfo[];
}
```

**After:**
```tsx
interface VideoTableProps {
  videos: VideoInfo[];
  onViewTranscript: (videoId: string, title: string) => void;
}
```

#### 3b. Update the function signature to destructure the new prop

**Before:**
```tsx
export function VideoTable({ videos }: VideoTableProps) {
```

**After:**
```tsx
export function VideoTable({ videos, onViewTranscript }: VideoTableProps) {
```

#### 3c. Add column header

**Before:**
```tsx
            <th>Transcript Source</th>
```

**After:**
```tsx
            <th>Transcript Source</th>
            <th></th>
```

#### 3d. Add button cell in each row

**Before:**
```tsx
              <td>{formatTranscriptSource(video.transcript_source, video.has_transcript)}</td>
            </tr>
```

**After:**
```tsx
              <td>{formatTranscriptSource(video.transcript_source, video.has_transcript)}</td>
              <td>
                {video.has_transcript && (
                  <button
                    className="view-transcript-btn"
                    onClick={() => onViewTranscript(video.video_id, video.title)}
                  >
                    View
                  </button>
                )}
              </td>
            </tr>
```

#### 3e. Add button styles to `App.css`

```css
.view-transcript-btn {
  padding: 4px 12px;
  font-size: 0.85rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.view-transcript-btn:hover {
  background: #2563eb;
}
```

### 4. Modify `App.tsx` — wire up state and render modal

#### 4a. Add import for TranscriptModal

Add to the imports section:
```tsx
import { TranscriptModal } from "./components/TranscriptModal";
```

#### 4b. Add state and handler

Add inside the `App` function, after the `useFetchTranscripts()` call:

```tsx
const [selectedVideo, setSelectedVideo] = useState<{
  videoId: string;
  title: string;
} | null>(null);

const handleViewTranscript = (videoId: string, title: string) => {
  setSelectedVideo({ videoId, title });
};

const handleCloseModal = () => {
  setSelectedVideo(null);
};
```

Also add `useState` to the React import (if not already imported):
```tsx
import { useState } from "react";
```

#### 4c. Pass callback to VideoTable

**Before:**
```tsx
      {videos.length > 0 && <VideoTable videos={videos} />}
```

**After:**
```tsx
      {videos.length > 0 && (
        <VideoTable videos={videos} onViewTranscript={handleViewTranscript} />
      )}
```

#### 4d. Render the modal

Add at the end of the JSX, just before the closing `</div>`:

```tsx
      {selectedVideo && (
        <TranscriptModal
          videoId={selectedVideo.videoId}
          title={selectedVideo.title}
          onClose={handleCloseModal}
        />
      )}
```

---

## Expected Final State

### Component Tree

```
App
├── FetchForm
├── ErrorMessage
├── ProgressBar
├── VideoProgressList
├── SummaryCard
├── VideoTable
│   └── "View" button (per row, if has_transcript)
└── TranscriptModal (conditional, when selectedVideo !== null)
    └── fetches GET /api/transcripts/{videoId}
```

### Data Flow

```
User clicks "View" button
  → VideoTable calls onViewTranscript(videoId, title)
  → App sets selectedVideo state
  → TranscriptModal mounts
  → Fetches GET /api/transcripts/{videoId}
  → Renders content in <pre> with preserved whitespace

User closes modal (X / Escape / click outside)
  → App sets selectedVideo to null
  → TranscriptModal unmounts
```

---

## Verification

1. Fetch a channel in the UI → table shows "View" button for videos with transcripts
2. Videos without transcripts have no "View" button
3. Click "View" → modal opens, shows "Loading transcript…" briefly, then content appears
4. Transcript content displays with proper line breaks and paragraphs
5. Click X → modal closes
6. Press Escape → modal closes
7. Click outside the modal (on overlay) → modal closes
8. If API returns 404 → modal shows error message
