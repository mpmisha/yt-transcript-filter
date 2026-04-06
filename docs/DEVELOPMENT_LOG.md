# Development Log — yt-transcript-filter

Chronological record of features developed in this project.

---

## Fetch Panel Web UI (V1)
**Date**: 2026-04-06
**Plan**: `src/Plans/FetchPanel/PLAN.md`

### Summary
Added a browser-based web UI for fetching YouTube transcripts. Users enter a channel/playlist URL, click Fetch, and see results populate progressively via Server-Sent Events.

### Changes
- **Files created**: `src/service.py`, `web/__init__.py`, `web/api.py`, `web/requirements.txt`, `web/frontend/` (full Vite + React + TypeScript app)
- **Key additions**:
  - Generator-based service layer (`src/service.py`) wrapping existing fetcher + storage modules
  - FastAPI SSE endpoint (`POST /api/fetch-transcripts`) with CORS and health check
  - React frontend with 5 components: FetchForm, VideoTable, ProgressBar, SummaryCard, ErrorMessage
  - Custom `useFetchTranscripts` hook for SSE stream parsing via ReadableStream
  - Vite proxy configuration for `/api` → `localhost:8000`

### Technical Details
Three-layer architecture: Python service generator → FastAPI streaming response → React SSE consumer. Communication uses Server-Sent Events for real-time progress streaming.

---

## Whisper Fallback Transcription
**Date**: 2026-04-06
**Plan**: `src/Plans/Whisper/PLAN_WHISPER.md`

### Summary
Added local Whisper-based speech-to-text as a fallback when YouTube captions are unavailable. Users toggle Whisper on/off and select a model size (tiny/base/small/medium).

### Changes
- **Files created**: `src/whisper_transcriber.py`
- **Files modified**: `src/fetcher.py`, `src/service.py`, `web/api.py`, `requirements.txt`, `.gitignore`, frontend types/components/hook/CSS
- **Key additions**:
  - `whisper_transcriber.py` with audio download (yt-dlp) + faster-whisper transcription + model caching
  - `fetch_transcript_with_fallback()` in fetcher.py returning `(text, source)` tuple
  - `whisper_model` parameter threaded through service → API → frontend
  - `transcript_source` field on SSE progress events ("youtube" / "whisper" / null)
  - Whisper toggle checkbox + model dropdown in FetchForm
  - Transcript source column in VideoTable, Whisper count in SummaryCard

### Technical Details
Whisper model is cached at module level for reuse across videos. Audio files are downloaded to `.audio_cache/` and cleaned up in a `finally` block after transcription.

---

## Detailed Progress Panel
**Date**: 2026-04-06
**Plan**: `src/Plans/Progress/PLAN.md`

### Summary
Added real-time per-video step tracking. The UI now shows all videos immediately after discovery and updates each video's status as processing progresses (checking captions → downloading audio → transcribing, etc.).

### Changes
- **Files modified**: `src/service.py`, `src/fetcher.py`, `src/whisper_transcriber.py`, frontend types/hook/App/CSS
- **Files created**: `web/frontend/src/components/VideoProgressList.tsx`
- **Key additions**:
  - `video_list` SSE event emitted immediately after video discovery (all videos shown as "pending")
  - `video_status` SSE events during processing with step labels (checking_captions, captions_found, downloading_audio, transcribing, whisper_complete, etc.)
  - Service.py rewritten to inline Whisper logic for true real-time `yield` between steps
  - `status_callback` parameter added to `fetch_transcript_with_fallback()` and `whisper_transcript()` for CLI path
  - VideoProgressList component with step icons (⬜⏳✅🎤❌⏭️), labels, color-coded states, and pulse animation

### Technical Details
The service generator now yields `video_status` events inline rather than using callbacks, enabling true real-time SSE streaming. The API layer required no changes — it already forwards all yielded dicts.

---

## Video Limit
**Date**: 2026-04-06
**Plan**: `src/Plans/VideoLimit/PLAN.md`

### Summary
Added an optional video limit parameter so users can cap the number of videos processed during a fetch. Applied after video discovery by slicing the list.

### Changes
- **Files modified**: `src/service.py`, `src/cli.py`, `web/api.py`, frontend FetchForm/hook/CSS
- **Key additions**:
  - `limit: int | None` parameter on `fetch_channel_transcripts()` — slices videos after discovery
  - `--limit` / `-n` CLI option on the `fetch` command
  - `limit: Optional[int] = Field(ge=1)` on the API request model with Pydantic validation
  - Number input with "All" placeholder in FetchForm, threaded through hook to API

### Technical Details
Limit is applied as a simple list slice (`videos[:limit]`) after `get_video_list()` returns. Everything downstream (video_list event, processing loop, done event) naturally uses the sliced list. Pydantic `ge=1` constraint auto-rejects invalid values with HTTP 422.

---
