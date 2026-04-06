> **Status: ✅ COMPLETED**

# Whisper Fallback Transcription — Development Plan

## Overview

Add local Whisper-based speech-to-text as a fallback when YouTube captions are unavailable. The user toggles Whisper on/off in the UI and selects a model size (tiny/base/small/medium). When enabled, videos without captions are automatically transcribed from audio.

## Architecture Change

```
Current:  YouTube URL → yt-dlp (video list) → youtube-transcript-api (captions) → save
New:      YouTube URL → yt-dlp (video list) → youtube-transcript-api (captions)
                                                    ↓ (if None + Whisper enabled)
                                               yt-dlp (audio) → faster-whisper → save
```

## Developer Tasks

Each task MUST be delegated to the correct specialized agent.

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Create the Whisper transcription module and integrate it into the service pipeline.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to create/modify:
- **Create** `src/whisper_transcriber.py` — audio download + Whisper transcription + model caching
- **Modify** `src/fetcher.py` — add `fetch_transcript_with_fallback()` function
- **Modify** `src/service.py` — accept `whisper_model` param, add `transcript_source` to events
- **Modify** `requirements.txt` — add `faster-whisper>=1.0.0`
- **Modify** `.gitignore` — add `.audio_cache/`

### Task 2 → Delegate to `@api-developer`

**API Developer**: Extend the FastAPI endpoint to accept and validate the `whisper_model` parameter.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- **Modify** `web/api.py` — add `whisper_model` to `FetchRequest`, validate allowed values, pass to service

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Add a Whisper toggle and model selector to the UI, update types and hook.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/types.ts` — add `WhisperModel`, `transcript_source` field
- **Modify** `web/frontend/src/components/FetchForm.tsx` — add toggle + model dropdown
- **Modify** `web/frontend/src/hooks/useFetchTranscripts.ts` — pass `whisper_model` in POST body
- **Modify** `web/frontend/src/components/VideoTable.tsx` — show transcript source column
- **Modify** `web/frontend/src/components/SummaryCard.tsx` — show Whisper count
- **Modify** `web/frontend/src/App.tsx` — wire new props

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Task 2 (API Dev)
                            │
Task 3 (FE Dev) ────────────┘ (integration)
```

- **Task 1 and Task 3** can start in parallel (no dependencies)
- **Task 2** starts once Task 1 is complete (needs the updated service signature)
- **Task 3** UI work is independent; SSE integration needs Task 2

## Updated Shared Contract

### API Endpoint (updated)

```
POST /api/fetch-transcripts
Content-Type: application/json

{
  "url": "https://www.youtube.com/@ChannelName/videos",
  "lang": "en",
  "whisper_model": "base"   // "tiny" | "base" | "small" | "medium" | null
}
```

### SSE Events (updated)

**Progress event** — now includes `transcript_source`:
```
data: {"event":"progress","current":1,"total":5,"video_id":"abc","title":"...","duration":180,"upload_date":"20240115","url":"https://...","has_transcript":true,"transcript_source":"youtube"}
data: {"event":"progress","current":2,"total":5,...,"has_transcript":true,"transcript_source":"whisper"}
data: {"event":"progress","current":3,"total":5,...,"has_transcript":false,"transcript_source":null}
```

**Done event** — now includes `with_whisper`:
```
data: {"event":"done","total":5,"with_transcript":4,"with_whisper":2,"output_dir":"./transcripts"}
```

### Allowed `whisper_model` Values

| Value | Behavior |
|-------|----------|
| `null` (or omitted) | Whisper disabled — current behavior, YouTube captions only |
| `"tiny"` | Fastest, lowest quality (~75MB model) |
| `"base"` | Balanced (~140MB model) |
| `"small"` | Good quality, slower (~460MB model) |
| `"medium"` | Best quality, slowest (~1.5GB model) |

## Verification

1. Fetch with Whisper **disabled** → identical to current behavior (no regression)
2. Fetch with Whisper `"base"` on a channel with no captions → videos get `transcript_source: "whisper"`
3. Mixed channel (some captioned, some not) → correct source labels per video
4. Invalid `whisper_model` value → API returns 400 error
5. Audio temp files cleaned up after transcription
6. UI toggle off → no `whisper_model` sent in request body
7. VideoTable shows correct source labels (YouTube / Whisper / None)
8. SummaryCard shows Whisper count when applicable
