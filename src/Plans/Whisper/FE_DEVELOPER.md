# FE Developer — Whisper Toggle & Model Selector

## Goal

Add a Whisper toggle and model size dropdown to the Fetch form. Update the types, hook, and table to handle the new `transcript_source` field so users can see which videos were transcribed by YouTube captions vs. Whisper.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/frontend/src/types.ts` — add `WhisperModel` type, `transcript_source` field |
| **Modify** | `web/frontend/src/components/FetchForm.tsx` — add toggle + model dropdown |
| **Modify** | `web/frontend/src/hooks/useFetchTranscripts.ts` — pass `whisper_model` in POST body |
| **Modify** | `web/frontend/src/components/VideoTable.tsx` — show transcript source |
| **Modify** | `web/frontend/src/components/SummaryCard.tsx` — show Whisper count |
| **Modify** | `web/frontend/src/App.tsx` — wire new props |

## Blocked By

Nothing for UI work (all components can be built independently). SSE integration needs the API Developer to be done.

## Delivers

Updated UI with Whisper toggle, model selector, and transcript source labels in the results table.

---

## Detailed Steps

### 1. Update `src/types.ts`

**Add new type:**
```typescript
export type WhisperModel = "tiny" | "base" | "small" | "medium";
```

**Add `transcript_source` to `VideoInfo`:**
```typescript
export interface VideoInfo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  upload_date: string | null;
  has_transcript: boolean;
  transcript_source: "youtube" | "whisper" | null;  // NEW
}
```

**Add `transcript_source` to `SSEProgressEvent`:**
```typescript
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
  transcript_source: "youtube" | "whisper" | null;  // NEW
}
```

**Add `with_whisper` to `SSEDoneEvent`:**
```typescript
export interface SSEDoneEvent {
  event: "done";
  total: number;
  with_transcript: number;
  with_whisper: number;  // NEW
  output_dir: string;
}
```

### 2. Update `FetchForm.tsx`

**Update props interface:**
```typescript
interface FetchFormProps {
  onSubmit: (url: string, lang: string, whisperModel: WhisperModel | null) => void;
  disabled: boolean;
}
```

**Add state for Whisper toggle and model selection:**
```typescript
const [whisperEnabled, setWhisperEnabled] = useState(false);
const [whisperModel, setWhisperModel] = useState<WhisperModel>("base");
```

**Update `handleSubmit`:**
```typescript
const handleSubmit = () => {
  if (!url.trim()) return;
  onSubmit(url.trim(), lang.trim() || "en", whisperEnabled ? whisperModel : null);
};
```

**Add UI elements** after the language input, before the Fetch button:

1. A checkbox/toggle labeled **"Auto-transcribe with Whisper"**
2. When checked, show a `<select>` dropdown with these options:

| Value | Display Label |
|-------|--------------|
| `tiny` | Tiny (fastest, basic quality) |
| `base` | Base (balanced) |
| `small` | Small (good quality, slower) |
| `medium` | Medium (best quality, slowest) |

3. Add an info note below the dropdown: `"First run downloads the model (~140MB for Base)"`

**Example JSX structure:**
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

### 3. Update `useFetchTranscripts.ts`

**Update `startFetch` signature:**

Current:
```typescript
const startFetch = useCallback(async (url: string, lang: string) => {
```

New:
```typescript
const startFetch = useCallback(async (url: string, lang: string, whisperModel: WhisperModel | null = null) => {
```

**Add `withWhisper` state:**
```typescript
const [withWhisper, setWithWhisper] = useState(0);
```

Reset it in `startFetch`:
```typescript
setWithWhisper(0);
```

**Update POST body:**

Current:
```typescript
body: JSON.stringify({ url, lang }),
```

New:
```typescript
body: JSON.stringify({ url, lang, whisper_model: whisperModel }),
```

**Update progress event handler** — include `transcript_source`:
```typescript
if (data.event === "progress") {
  setVideos((prev) => [
    ...prev,
    {
      video_id: data.video_id,
      title: data.title,
      url: data.url,
      duration: data.duration,
      upload_date: data.upload_date,
      has_transcript: data.has_transcript,
      transcript_source: data.transcript_source,  // NEW
    },
  ]);
  setProgress({ current: data.current, total: data.total });
}
```

**Update done event handler** — capture `with_whisper`:
```typescript
} else if (data.event === "done") {
  setWithTranscript(data.with_transcript);
  setWithWhisper(data.with_whisper);  // NEW
  setStatus("done");
}
```

**Update return value:**
```typescript
return { videos, progress, status, error, withTranscript, withWhisper, startFetch };
```

**Update `UseFetchResult` interface:**
```typescript
interface UseFetchResult {
  videos: VideoInfo[];
  progress: FetchProgress;
  status: FetchStatus;
  error: string | null;
  withTranscript: number;
  withWhisper: number;  // NEW
  startFetch: (url: string, lang: string, whisperModel: WhisperModel | null) => void;
}
```

### 4. Update `VideoTable.tsx`

**Change the Transcript column** to show the source:

Current:
```tsx
<td>{video.has_transcript ? "✅" : "❌"}</td>
```

New:
```tsx
<td>{formatTranscriptSource(video.transcript_source, video.has_transcript)}</td>
```

**Add helper function:**
```typescript
function formatTranscriptSource(source: string | null, hasTranscript: boolean): string {
  if (!hasTranscript) return "❌ None";
  if (source === "youtube") return "✅ YouTube";
  if (source === "whisper") return "✅ Whisper";
  return "✅";
}
```

**Update column header** from `"Transcript"` to `"Transcript Source"`.

### 5. Update `SummaryCard.tsx`

**Update props:**
```typescript
interface SummaryCardProps {
  total: number;
  withTranscript: number;
  withWhisper: number;  // NEW
}
```

**Update display** to show Whisper count when applicable:
```tsx
<p>✅ {withTranscript} / {total} videos have transcripts</p>
{withWhisper > 0 && (
  <p>🎤 {withWhisper} transcribed by Whisper</p>
)}
```

### 6. Update `App.tsx`

**Update hook destructuring:**

Current:
```typescript
const { videos, progress, status, error, withTranscript, startFetch } = useFetchTranscripts();
```

New:
```typescript
const { videos, progress, status, error, withTranscript, withWhisper, startFetch } = useFetchTranscripts();
```

**Update `SummaryCard` props:**

Current:
```tsx
<SummaryCard total={progress.total} withTranscript={withTranscript} />
```

New:
```tsx
<SummaryCard total={progress.total} withTranscript={withTranscript} withWhisper={withWhisper} />
```

---

## Styling Notes

Use Tailwind utility classes for the new Whisper controls. Example patterns:

- Toggle container: `flex items-center gap-2 mt-2`
- Checkbox: default HTML `<input type="checkbox">` (Tailwind doesn't style checkboxes by default — use `accent-blue-600` for color)
- Dropdown: `rounded border border-gray-300 px-2 py-1 text-sm`
- Info text: `text-xs text-gray-500 mt-1`

---

## Verification

1. **Toggle off**: Enter URL, leave Whisper unchecked → request body has `whisper_model: null`, behavior identical to before
2. **Toggle on**: Check Whisper, select "Base" → request body has `whisper_model: "base"`
3. **Dropdown hidden**: When toggle is unchecked, model dropdown is not visible
4. **Dropdown visible**: When toggle is checked, dropdown appears with 4 options
5. **Table labels**: Videos show "YouTube", "Whisper", or "None" in the Transcript Source column
6. **Summary card**: Shows "🎤 N transcribed by Whisper" when applicable
7. **Disabled state**: Toggle and dropdown are disabled while fetching

## Definition of Done

- [ ] `types.ts` has `WhisperModel` type and `transcript_source` field on `VideoInfo` and `SSEProgressEvent`
- [ ] `SSEDoneEvent` has `with_whisper` field
- [ ] `FetchForm` has Whisper toggle checkbox and model dropdown
- [ ] Dropdown is hidden when toggle is off, shown when on
- [ ] `useFetchTranscripts` sends `whisper_model` in POST body
- [ ] `useFetchTranscripts` tracks and returns `withWhisper` count
- [ ] `VideoTable` shows transcript source (YouTube / Whisper / None)
- [ ] `SummaryCard` shows Whisper count when > 0
- [ ] `App.tsx` wires `withWhisper` to `SummaryCard`
- [ ] All controls disabled during loading
- [ ] Info note about model download is visible when toggle is on
