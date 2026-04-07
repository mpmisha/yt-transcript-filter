# FE Developer — Skip Reason Messages

## Goal

Display the skip reason in the progress list. The existing wiring already handles this — verify it works and optionally polish the display.

## Files

| Action | File |
|--------|------|
| **Modify** | `web/frontend/src/components/VideoProgressList.tsx` |

## Blocked By

Nothing — can start in parallel with BE work. The `error` field already exists on `VideoProgressItem` and is already mapped from SSE events in `useFetchTranscripts.ts`.

## Delivers

Skipped videos in the progress list show a descriptive reason (e.g. "Transcripts disabled by uploader") instead of just "Skipped".

---

## Detailed Steps

### What already works

- `SSEVideoStatusEvent` has `error?: string` in `types.ts`
- `VideoProgressItem` has `error?: string` in `types.ts`
- `useFetchTranscripts.ts` maps `data.error` to `item.error` in the `video_status` handler
- `VideoProgressList.tsx` already renders `item.error` when present:
  ```tsx
  {item.error && (
    <span className="video-progress-error">{item.error}</span>
  )}
  ```

### What to verify/adjust

The existing render for skipped items will show:
```
⏭️  Video Title    Skipped    Transcripts disabled by uploader
```

This works out of the box once the BE populates the `error` field. No structural change is strictly required.

**Optional polish**: If the "Skipped" label feels redundant next to the reason, change `getStepLabel("skipped")` to return `"Skipped:"` (with colon) so it reads more naturally as a prefix to the reason.

### What NOT to change

- **`types.ts`** — No changes. `SSEVideoStatusEvent` already has `error?: string`, `VideoProgressItem` already has `error?: string`
- **`useFetchTranscripts.ts`** — No changes. Already maps `data.error` to `item.error`
- **`VideoTable.tsx`** — No changes. The results table shows `has_transcript` and `transcript_source`, not skip reasons

---

## Verification

1. Fetch a channel where some videos have no transcripts → progress list shows ⏭️ icon with reason text like "No transcript available"
2. Rate-limited videos show "Skipped — YouTube rate limited a previous request"
3. Videos with transcripts found show ✅ as before (no error span)
4. Cached videos show 📦 as before (no error span)
5. `npx tsc --noEmit` → no TypeScript errors
