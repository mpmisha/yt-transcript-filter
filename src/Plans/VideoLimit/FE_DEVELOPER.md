# FE Developer — Video Limit

## Goal

Add a number input field to the fetch form so users can optionally limit how many videos to process. Thread the value through the hook to the API request body.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/frontend/src/components/FetchForm.tsx` — add limit number input |
| **Modify** | `web/frontend/src/hooks/useFetchTranscripts.ts` — add `limit` param to `startFetch()` |
| **Modify** | `web/frontend/src/App.tsx` — update `onSubmit` signature if needed |

## Blocked By

Nothing — can start immediately. The API/BE changes are backwards-compatible (omitting `limit` means "all").

## Delivers

A video limit input in the UI that sends the value to the API.

---

## Step 1: Update `useFetchTranscripts.ts` hook

### Update `startFetch` signature

Current:
```typescript
startFetch: (url: string, lang: string, whisperModel?: WhisperModel | null) => void;
```

New:
```typescript
startFetch: (url: string, lang: string, whisperModel?: WhisperModel | null, limit?: number | null) => void;
```

### Update the `useCallback` implementation

Current signature:
```typescript
const startFetch = useCallback(async (url: string, lang: string, whisperModel: WhisperModel | null = null) => {
```

New:
```typescript
const startFetch = useCallback(async (url: string, lang: string, whisperModel: WhisperModel | null = null, limit: number | null = null) => {
```

### Update request body

Current:
```typescript
body: JSON.stringify({ url, lang, whisper_model: whisperModel }),
```

New:
```typescript
body: JSON.stringify({
  url,
  lang,
  whisper_model: whisperModel,
  ...(limit != null && { limit }),
}),
```

The spread ensures `limit` is only included when set (not `null`/`undefined`), keeping backwards compatibility.

---

## Step 2: Update `FetchForm.tsx`

### Update props interface

Current:
```typescript
interface FetchFormProps {
  onSubmit: (url: string, lang: string, whisperModel: WhisperModel | null) => void;
  disabled: boolean;
}
```

New:
```typescript
interface FetchFormProps {
  onSubmit: (url: string, lang: string, whisperModel: WhisperModel | null, limit: number | null) => void;
  disabled: boolean;
}
```

### Add state for limit

Add alongside existing state:
```typescript
const [limit, setLimit] = useState<string>("");
```

Use `string` for the input value to allow empty state (meaning "all"). Convert to `number | null` on submit.

### Update `handleSubmit`

Current:
```typescript
const handleSubmit = () => {
  if (!url.trim()) return;
  onSubmit(url.trim(), lang.trim() || "en", whisperEnabled ? whisperModel : null);
};
```

New:
```typescript
const handleSubmit = () => {
  if (!url.trim()) return;
  const parsedLimit = limit.trim() ? parseInt(limit.trim(), 10) : null;
  const validLimit = parsedLimit !== null && parsedLimit >= 1 ? parsedLimit : null;
  onSubmit(url.trim(), lang.trim() || "en", whisperEnabled ? whisperModel : null, validLimit);
};
```

### Add number input to JSX

Add after the language input and before the Fetch button:

```tsx
<input
  type="number"
  className="limit-input"
  placeholder="All"
  min={1}
  value={limit}
  onChange={(e) => setLimit(e.target.value)}
  onKeyDown={handleKeyDown}
  disabled={disabled}
/>
```

### Add CSS for the input

Add to `App.css` alongside existing form input styles:

```css
.limit-input {
  width: 80px;
  text-align: center;
}
```

The input inherits existing form input styling. The narrow width keeps the form compact since limit values are short numbers.

---

## Step 3: Verify `App.tsx`

The current `App.tsx` passes `startFetch` directly as the `onSubmit` prop:

```tsx
<FetchForm onSubmit={startFetch} disabled={status === "loading"} />
```

Since `startFetch` now accepts an optional 4th parameter and `FetchForm` passes 4 arguments, **no changes to `App.tsx` are needed** — the function signatures are compatible.

---

## UI Layout

The limit input sits between the language input and the Fetch button:

```
[URL ═══════════════════════════════] [en] [All] [Fetch]
[☑ Auto-transcribe with Whisper] [Base ▼]
```

- Placeholder text: "All" (when empty, means no limit)
- Input type: `number` (only accepts digits, shows spinner on desktop)
- Min value: `1` (HTML constraint + JS validation)

---

## Edge Cases

1. **Empty input** → `null` → no limit (all videos)
2. **Value of 0** → treated as `null` (validation filters it out)
3. **Negative value** → treated as `null` (validation filters it out)
4. **Non-numeric text** → `type="number"` prevents this in most browsers
5. **Very large number** → works fine (processes all videos if fewer exist)
6. **Value of 1** → processes exactly 1 video

---

## Verification

1. Leave limit empty, fetch → all videos processed (unchanged behavior)
2. Set limit to 3, fetch → `video_list` shows 3 videos, progress bar goes to 3/3
3. Set limit to 1, fetch → only 1 video processed
4. Clear limit after a run, fetch again → all videos processed
5. Type 0 or negative → treated as "All" (no limit sent)
6. `npm run build` passes with no TypeScript errors

## Definition of Done

- [ ] `startFetch()` accepts optional `limit: number | null` parameter
- [ ] Request body includes `limit` only when set (not null)
- [ ] `FetchFormProps.onSubmit` accepts 4th `limit` parameter
- [ ] Number input added to form with placeholder "All"
- [ ] Empty/zero/negative values are treated as "no limit"
- [ ] Input disabled during loading
- [ ] No TypeScript errors (`npm run build` passes)
