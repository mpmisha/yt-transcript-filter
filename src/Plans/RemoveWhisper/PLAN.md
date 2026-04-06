# Remove Whisper Fallback — Development Plan

## Overview

Remove the entire Whisper-based fallback transcription system from all three layers (BE, API, FE). YouTube's auto-generated captions cover the vast majority of videos, making the Whisper path unnecessary. Removing it eliminates the `faster-whisper` dependency, heavy yt-dlp audio downloads, and the associated rate-limiting risk.

## Motivation

- YouTube auto-generates captions for virtually all spoken-audio videos — the Whisper fallback is rarely needed
- The Whisper path downloads full audio streams via yt-dlp, which triggers aggressive YouTube rate-limiting (429 errors) after ~10-20 videos
- The transcript API is much lighter (~100-200+ requests before issues) and sufficient for the use case
- Removes `faster-whisper` dependency (~140MB+ model downloads)
- Simplifies the codebase significantly (~57 Whisper references across 13 files)

## Architecture Change

```
Current:  YouTube URL → yt-dlp (video list) → youtube-transcript-api (captions)
                                                    ↓ (if None + Whisper enabled)
                                               yt-dlp (audio) → faster-whisper → save

New:      YouTube URL → yt-dlp (video list) → youtube-transcript-api (captions) → save
```

## Developer Tasks

Each task MUST be delegated to the correct specialized agent.

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Delete the Whisper module and remove Whisper references from the service pipeline.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Delete** `src/whisper_transcriber.py` — entire file
- **Modify** `src/fetcher.py` — remove `fetch_transcript_with_fallback()` function
- **Modify** `src/service.py` — remove `whisper_model` param, Whisper branch, `with_whisper` tracking
- **Modify** `requirements.txt` — remove `faster-whisper>=1.0.0`
- **Modify** `.gitignore` — remove `.audio_cache/`

### Task 2 → Delegate to `@api-developer`

**API Developer**: Remove Whisper fields from the API request model and validation.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- **Modify** `web/api.py` — remove `VALID_WHISPER_MODELS`, `whisper_model` from `FetchRequest`, validation block, service call arg

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Remove all Whisper UI, types, state, and CSS.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/types.ts` — remove `WhisperModel`, Whisper video steps, `with_whisper`
- **Modify** `web/frontend/src/components/FetchForm.tsx` — remove Whisper toggle UI and state
- **Modify** `web/frontend/src/hooks/useFetchTranscripts.ts` — remove `whisperModel` param, `withWhisper` state
- **Modify** `web/frontend/src/components/VideoProgressList.tsx` — remove Whisper step cases
- **Modify** `web/frontend/src/components/VideoTable.tsx` — remove Whisper source display
- **Modify** `web/frontend/src/components/SummaryCard.tsx` — remove `withWhisper` prop
- **Modify** `web/frontend/src/App.tsx` — remove `withWhisper` wiring
- **Modify** `web/frontend/src/App.css` — remove `.whisper-*` CSS classes

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Task 2 (API Dev)
                            │
Task 3 (FE Dev) ────────────┘ (integration)
```

- **Task 1 and Task 3** can start in parallel (no dependencies)
- **Task 2** starts once Task 1 is complete (needs the updated service signature)
- **Task 3** UI work is independent; can be done in parallel with Task 1

## Updated Shared Contract

### API Endpoint (updated)

```
POST /api/fetch-transcripts
Content-Type: application/json

{
  "url": "https://www.youtube.com/@ChannelName/videos",
  "lang": "en",
  "limit": 10
}
```

**Removed field:** `whisper_model`

### SSE Events (updated)

**Progress event** — `transcript_source` simplified:
```json
{
  "event": "progress",
  "video_id": "abc123",
  "title": "Video Title",
  "has_transcript": true,
  "transcript_source": "youtube"
}
```

`transcript_source` is now `"youtube" | null` (no more `"whisper"`).

**Done event** — `with_whisper` removed:
```json
{
  "event": "done",
  "total": 10,
  "with_transcript": 8,
  "output_dir": "./transcripts"
}
```

**Removed video_status steps:** `downloading_audio`, `transcribing`, `whisper_complete`, `whisper_failed`

**Remaining video_status steps:** `checking_captions`, `captions_found`, `no_captions`, `skipped`

## Verification

1. `python3 -c "from src.service import fetch_channel_transcripts; print('OK')"` — no import errors
2. `cd web/frontend && npx tsc --noEmit` — no TypeScript errors
3. Start dev servers (`npm run dev`), fetch a channel with limit=1 — works without Whisper UI
4. `grep -ri whisper src/ web/` — returns nothing
5. `grep -ri faster.whisper requirements.txt pyproject.toml` — returns nothing
