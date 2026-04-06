# FE Developer — Remove Whisper from Frontend

## Goal

Remove all Whisper-related UI, types, state, and CSS from the frontend. This includes the Whisper toggle/model selector in FetchForm, Whisper-specific video steps in VideoProgressList, Whisper count in SummaryCard, and the WhisperModel type.

## Files

| Action | Path |
|--------|------|
| **Modify** | `web/frontend/src/types.ts` |
| **Modify** | `web/frontend/src/components/FetchForm.tsx` |
| **Modify** | `web/frontend/src/hooks/useFetchTranscripts.ts` |
| **Modify** | `web/frontend/src/components/VideoProgressList.tsx` |
| **Modify** | `web/frontend/src/components/VideoTable.tsx` |
| **Modify** | `web/frontend/src/components/SummaryCard.tsx` |
| **Modify** | `web/frontend/src/App.tsx` |
| **Modify** | `web/frontend/src/App.css` |

## Blocked By

Nothing — all UI changes are independent. Can start in parallel with BE Developer.

## Delivers

A simplified frontend with no Whisper UI, no WhisperModel type, and no Whisper-related state or SSE handling.

---

## Detailed Steps

### 1. Modify `types.ts` — Remove Whisper types

#### 1a. Remove `WhisperModel` type

**Remove:**
```typescript
export type WhisperModel = "tiny" | "base" | "small" | "medium";
```

#### 1b. Simplify `transcript_source` in `VideoInfo`

**Before:**
```typescript
transcript_source: "youtube" | "whisper" | null;
```

**After:**
```typescript
transcript_source: "youtube" | null;
```

#### 1c. Simplify `transcript_source` in `SSEProgressEvent`

Same change — `"youtube" | "whisper" | null` → `"youtube" | null`.

#### 1d. Remove `with_whisper` from `SSEDoneEvent`

**Before:**
```typescript
export interface SSEDoneEvent {
  event: "done";
  total: number;
  with_transcript: number;
  with_whisper: number;
  output_dir: string;
}
```

**After:**
```typescript
export interface SSEDoneEvent {
  event: "done";
  total: number;
  with_transcript: number;
  output_dir: string;
}
```

#### 1e. Remove Whisper steps from `VideoStep` union

**Before:**
```typescript
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
```

**After:**
```typescript
export type VideoStep =
  | "pending"
  | "checking_captions"
  | "captions_found"
  | "no_captions"
  | "skipped";
```

---

### 2. Modify `FetchForm.tsx` — Remove Whisper toggle UI

#### 2a. Remove `WhisperModel` import

**Remove:**
```typescript
import type { WhisperModel } from "../types";
```

#### 2b. Simplify `FetchFormProps.onSubmit` signature

**Before:**
```typescript
onSubmit: (url: string, lang: string, whisperModel: WhisperModel | null, limit: number | null) => void;
```

**After:**
```typescript
onSubmit: (url: string, lang: string, limit: number | null) => void;
```

#### 2c. Remove Whisper state variables

**Remove:**
```typescript
const [whisperEnabled, setWhisperEnabled] = useState(true);
const [whisperModel, setWhisperModel] = useState<WhisperModel>("base");
```

#### 2d. Simplify `handleSubmit`

**Before:**
```typescript
onSubmit(url.trim(), "en", whisperEnabled ? whisperModel : null, validLimit);
```

**After:**
```typescript
onSubmit(url.trim(), "en", validLimit);
```

#### 2e. Remove Whisper toggle JSX

**Remove the entire `<div className="whisper-toggle">` block** (lines 50-75 in the current file):

```tsx
      <div className="whisper-toggle">
        <label>
          <input
            type="checkbox"
            checked={whisperEnabled}
            onChange={(e) => setWhisperEnabled(e.target.checked)}
            disabled={disabled}
          />
          Auto-transcribe with Whisper
        </label>
        {whisperEnabled && (
          <div className="whisper-model-select">
            <select
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value as WhisperModel)}
              disabled={disabled}
            >
              <option value="tiny">Tiny (fastest, basic quality)</option>
              <option value="base">Base (balanced)</option>
              <option value="small">Small (good quality, slower)</option>
              <option value="medium">Medium (best quality, slowest)</option>
            </select>
            <p className="whisper-info">First run downloads the model (~140MB for Base)</p>
          </div>
        )}
      </div>
```

Also remove the `useState` import if it's no longer used (it will still be needed for `url` and `limit` state).

---

### 3. Modify `useFetchTranscripts.ts` — Remove Whisper from hook

#### 3a. Remove `WhisperModel` from import

**Before:**
```typescript
import type { VideoInfo, VideoProgressItem, FetchProgress, FetchStatus, SSEEvent, WhisperModel } from "../types";
```

**After:**
```typescript
import type { VideoInfo, VideoProgressItem, FetchProgress, FetchStatus, SSEEvent } from "../types";
```

#### 3b. Remove `withWhisper` from return type

**Remove from `UseFetchResult`:**
```typescript
withWhisper: number;
```

#### 3c. Simplify `startFetch` signature

**Before:**
```typescript
startFetch: (url: string, lang: string, whisperModel?: WhisperModel | null, limit?: number | null) => void;
```

**After:**
```typescript
startFetch: (url: string, lang: string, limit?: number | null) => void;
```

#### 3d. Remove `withWhisper` state

**Remove:**
```typescript
const [withWhisper, setWithWhisper] = useState(0);
```

#### 3e. Simplify `startFetch` callback

**Before:**
```typescript
const startFetch = useCallback(async (url: string, lang: string, whisperModel: WhisperModel | null = null, limit: number | null = null) => {
```

**After:**
```typescript
const startFetch = useCallback(async (url: string, lang: string, limit: number | null = null) => {
```

**Remove from reset block:**
```typescript
setWithWhisper(0);
```

#### 3f. Remove `whisper_model` from API request body

**Before:**
```typescript
body: JSON.stringify({
  url,
  lang,
  whisper_model: whisperModel,
  ...(limit != null && { limit }),
}),
```

**After:**
```typescript
body: JSON.stringify({
  url,
  lang,
  ...(limit != null && { limit }),
}),
```

#### 3g. Remove `setWithWhisper` from done handler

**Before:**
```typescript
} else if (data.event === "done") {
  setWithTranscript(data.with_transcript);
  setWithWhisper(data.with_whisper);
  setStatus("done");
}
```

**After:**
```typescript
} else if (data.event === "done") {
  setWithTranscript(data.with_transcript);
  setStatus("done");
}
```

#### 3h. Remove `withWhisper` from return

**Before:**
```typescript
return { videos, videoProgress, progress, status, error, withTranscript, withWhisper, startFetch };
```

**After:**
```typescript
return { videos, videoProgress, progress, status, error, withTranscript, startFetch };
```

---

### 4. Modify `VideoProgressList.tsx` — Remove Whisper step cases

Remove these cases from all three `switch` functions (`getStepIcon`, `getStepLabel`, `getStepClass`):

#### `getStepIcon` — Remove:
```typescript
case "downloading_audio":
case "transcribing":
    return "⏳";
// ...
case "whisper_complete":
    return "🎤";
case "whisper_failed":
    return "❌";
```

Keep `checking_captions` returning `"⏳"` (it currently shares a case with `downloading_audio` and `transcribing` — make sure it still returns `"⏳"` on its own).

**Before:**
```typescript
case "checking_captions":
case "downloading_audio":
case "transcribing":
    return "⏳";
```

**After:**
```typescript
case "checking_captions":
    return "⏳";
```

#### `getStepLabel` — Remove:
```typescript
case "downloading_audio":
    return "Downloading audio…";
case "transcribing":
    return "Transcribing…";
case "whisper_complete":
    return "Whisper (complete)";
case "whisper_failed":
    return "Whisper (failed)";
```

#### `getStepClass` — Remove:
```typescript
case "downloading_audio":
case "transcribing":
    return "step-active";
// ...
case "whisper_complete":
    return "step-success";
// ...
case "whisper_failed":
    return "step-error";
```

Keep `checking_captions` returning `"step-active"` on its own.

**Before:**
```typescript
case "checking_captions":
case "downloading_audio":
case "transcribing":
    return "step-active";
```

**After:**
```typescript
case "checking_captions":
    return "step-active";
```

---

### 5. Modify `VideoTable.tsx` — Remove Whisper source

**Remove this line from `formatTranscriptSource`:**
```typescript
if (source === "whisper") return "✅ Whisper";
```

The function should now be:
```typescript
function formatTranscriptSource(source: string | null, hasTranscript: boolean): string {
  if (!hasTranscript) return "❌ None";
  if (source === "youtube") return "✅ YouTube";
  return "✅";
}
```

---

### 6. Modify `SummaryCard.tsx` — Remove `withWhisper` prop

**Before:**
```typescript
interface SummaryCardProps {
  total: number;
  withTranscript: number;
  withWhisper: number;
}

export function SummaryCard({ total, withTranscript, withWhisper }: SummaryCardProps) {
  return (
    <div className="summary-card">
      <p>✅ {withTranscript} / {total} videos have transcripts</p>
      {withWhisper > 0 && (
        <p>🎤 {withWhisper} transcribed by Whisper</p>
      )}
    </div>
  );
}
```

**After:**
```typescript
interface SummaryCardProps {
  total: number;
  withTranscript: number;
}

export function SummaryCard({ total, withTranscript }: SummaryCardProps) {
  return (
    <div className="summary-card">
      <p>✅ {withTranscript} / {total} videos have transcripts</p>
    </div>
  );
}
```

---

### 7. Modify `App.tsx` — Remove `withWhisper` wiring

#### 7a. Remove `withWhisper` from hook destructure

**Before:**
```typescript
const { videos, videoProgress, progress, status, error, withTranscript, withWhisper, startFetch } =
    useFetchTranscripts();
```

**After:**
```typescript
const { videos, videoProgress, progress, status, error, withTranscript, startFetch } =
    useFetchTranscripts();
```

#### 7b. Remove `withWhisper` from SummaryCard props

**Before:**
```tsx
<SummaryCard
  total={progress.total}
  withTranscript={withTranscript}
  withWhisper={withWhisper}
/>
```

**After:**
```tsx
<SummaryCard
  total={progress.total}
  withTranscript={withTranscript}
/>
```

---

### 8. Modify `App.css` — Remove Whisper CSS classes

**Remove the entire Whisper Toggle CSS section** (the comment and all 6 class rules):

```css
/* Whisper Toggle */
.whisper-toggle {
  margin-bottom: 1rem;
}

.whisper-toggle label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  cursor: pointer;
}

.whisper-toggle input[type="checkbox"] {
  accent-color: #4361ee;
  width: 16px;
  height: 16px;
}

.whisper-model-select {
  margin-top: 0.5rem;
  margin-left: 1.5rem;
}

.whisper-model-select select {
  padding: 0.4rem 0.6rem;
  border: 1px solid #ccc;
  border-radius: 6px;
  font-size: 0.9rem;
}

.whisper-info {
  margin-top: 0.3rem;
  font-size: 0.8rem;
  color: #888;
}
```

---

## Verification

1. `cd web/frontend && npx tsc --noEmit` — no TypeScript errors
2. `cd web/frontend && npm run build` — builds successfully
3. `grep -ri whisper web/frontend/src/` — returns nothing
4. Start dev servers, load the UI — no Whisper toggle visible, fetch works with captions only
5. Fetch a channel with limit=1 — SummaryCard shows transcript count without Whisper line
