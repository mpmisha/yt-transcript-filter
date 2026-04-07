# FE Developer — Skip Already-Fetched Transcripts

## Goal

Add `"cached"` to the `VideoStep` type and `transcript_source` type, and update display components to show a distinct icon/label for cached transcripts.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/frontend/src/types.ts` |
| **Modify** | `web/frontend/src/components/VideoProgressList.tsx` |
| **Modify** | `web/frontend/src/components/VideoTable.tsx` |

## Blocked By

Nothing — can start in parallel with BE work.

## Delivers

The UI distinguishes cached transcripts from freshly fetched ones with unique icons, labels, and source text.

---

## Detailed Steps

### 1. Update `types.ts`

#### 1a. Add `"cached"` to `VideoStep`

**Before:**
```typescript
export type VideoStep =
  | "pending"
  | "checking_captions"
  | "captions_found"
  | "no_captions"
  | "skipped";
```

**After:**
```typescript
export type VideoStep =
  | "pending"
  | "checking_captions"
  | "captions_found"
  | "no_captions"
  | "skipped"
  | "cached";
```

#### 1b. Add `"cached"` to `transcript_source` in `VideoInfo` and `SSEProgressEvent`

**Before (in both interfaces):**
```typescript
  transcript_source: "youtube" | null;
```

**After:**
```typescript
  transcript_source: "youtube" | "cached" | null;
```

### 2. Update `VideoProgressList.tsx`

Add `"cached"` case to all three switch functions:

**In `getStepIcon()`:**
```typescript
    case "cached":
      return "📦";
```

**In `getStepLabel()`:**
```typescript
    case "cached":
      return "Cached locally";
```

**In `getStepClass()`:**
```typescript
    case "cached":
      return "step-success";
```

### 3. Update `VideoTable.tsx`

Update the `formatTranscriptSource()` function:

**Before:**
```typescript
function formatTranscriptSource(source: string | null, hasTranscript: boolean): string {
  if (!hasTranscript) return "❌ None";
  if (source === "youtube") return "✅ YouTube";
  return "✅";
}
```

**After:**
```typescript
function formatTranscriptSource(source: string | null, hasTranscript: boolean): string {
  if (!hasTranscript) return "❌ None";
  if (source === "youtube") return "✅ YouTube";
  if (source === "cached") return "📦 Cached";
  return "✅";
}
```

---

## Verification

1. Fetch a channel → progress list shows ⏳/✅ icons as before
2. Re-fetch same channel → progress list shows 📦 "Cached locally" for all videos
3. Results table shows "📦 Cached" in transcript source column for cached videos
4. `npx tsc --noEmit` → no TypeScript errors
