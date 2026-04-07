# Documentation Agent — Skip Already-Fetched Transcripts

## Goal

After all code changes are implemented, update project documentation to reflect the new cache-aware transcript fetching.

## When to Run

After Task 1 (BE Developer) and Task 2 (FE Developer) are complete and verified.

## Trigger

Run `@documentation` with context: "The SkipCached plan has been implemented. Update docs."

## What to Update

### 1. README.md

- Add to Features list: "**Smart caching** — re-scraping a channel skips already-fetched transcripts, minimizing YouTube API calls"
- Update the Progress Panel section to mention the 📦 cached state

### 2. docs/DEVELOPMENT_LOG.md

Append a new entry:
```markdown
## Skip Already-Fetched Transcripts
**Date**: {today's date}
**Plan**: `src/Plans/SkipCached/PLAN.md`

### Summary
Re-scraping a channel now skips videos whose transcripts are already stored locally. Only new videos or previously-failed fetches (has_transcript: false) trigger YouTube API calls. Cached videos get a distinct "📦 Cached" indicator in both the progress panel and results table.

### Changes
- **Files modified**: `src/storage.py`, `src/service.py`, `web/frontend/src/types.ts`, `web/frontend/src/components/VideoProgressList.tsx`, `web/frontend/src/components/VideoTable.tsx`
- **Key additions**:
  - `extract_transcript_body()` in storage.py — strips Markdown header to extract raw transcript
  - Cache lookup in service.py using `_index.json` entries with `has_transcript: true`
  - Index merging after save — preserves entries from previous runs not in current batch
  - `"cached"` added to `VideoStep` type and `transcript_source` type
  - 📦 icon/label in progress list and "📦 Cached" in transcript source column

### Technical Details
- Rate limiting (1.5s sleep) only applied between actual API calls, not after cached reads
- Cache validity requires: video_id in index + has_transcript is true + .md file body is non-empty
- Metadata-only .md files (has_transcript: false) are re-fetched
```

### 3. web/frontend/README.md

No changes needed (component descriptions already generic enough).

## Reference

- Plan file: `src/Plans/SkipCached/PLAN.md`
- Implementation files: `src/storage.py`, `src/service.py`, frontend types/components
