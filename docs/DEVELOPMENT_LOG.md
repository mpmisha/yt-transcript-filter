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

## Markdown Transcript Formatting
**Date**: 2026-04-06
**Plan**: `src/Plans/TranscriptFormatting/PLAN.md`

### Summary
Transcripts are now saved as formatted Markdown (`.md`) instead of raw text (`.txt`). Each file includes a title heading, video metadata block (URL, ID, upload date, duration), and paragraphs split on speaker-change markers (`>>`).

### Changes
- **Files modified**: `src/storage.py`
- **Key additions**:
  - `format_transcript_as_markdown()` — formats a `VideoInfo` into a structured Markdown document
  - `_format_duration()` and `_format_upload_date()` private helper functions
  - Transcript files now use `.md` extension instead of `.txt`
  - `_index.json` references `.md` filenames
  - Videos without transcripts get a metadata-only Markdown file (no `[No transcript available]` placeholder)

### Technical Details
The formatter is a pure function in `src/storage.py` — no new modules, no external dependencies. YouTube auto-generated captions include `>>` markers at speaker changes, which are used as natural paragraph break points. No retroactive conversion of existing `.txt` files. The `load_index()` and `load_transcript()` functions required no changes since they read filenames from `_index.json`.

---

## Transcript Viewer Modal
**Date**: 2026-04-06
**Plan**: `src/Plans/TranscriptViewer/PLAN.md`

### Summary
Added a "View" button in the video table that opens a modal overlay displaying the full formatted transcript. Transcripts are served via a new `GET /api/transcripts/{video_id}` API endpoint.

### Changes
- **Files created**: `web/frontend/src/components/TranscriptModal.tsx`
- **Files modified**: `web/api.py`, `web/frontend/src/components/VideoTable.tsx`, `web/frontend/src/App.tsx`, `web/frontend/src/App.css`
- **Key additions**:
  - `GET /api/transcripts/{video_id}` endpoint using existing `load_index()` and `load_transcript()` from storage
  - `TranscriptModal` component with fetch-on-mount, loading/error states, close via X/Escape/overlay click
  - "View" button column in VideoTable (only shown for videos with transcripts)
  - `selectedVideo` state in App.tsx to control modal visibility
  - Modal and button CSS styles

### Technical Details
The API endpoint uses existing storage functions — no new backend code was needed. Transcript content is rendered as preformatted text (`<pre>` with `white-space: pre-wrap`) to preserve the Markdown formatting without parsing it as HTML, avoiding XSS risks. Three close mechanisms: X button, Escape key (via `keydown` listener), and overlay click (target === currentTarget check).

---

## Default Transcript View on Load
**Date**: 2026-04-06
**Plan**: `src/Plans/DefaultView/PLAN.md`

### Summary
Added automatic loading of existing transcripts when the app starts, so users immediately see saved results without running a new fetch.

### Changes
- **Files created**: None
- **Files modified**: `web/api.py`, `web/frontend/src/hooks/useFetchTranscripts.ts`
- **Key additions**:
  - New `GET /api/transcripts` endpoint that returns index-backed video rows and counts
  - `useFetchTranscripts` now calls `GET /api/transcripts` on mount
  - Hook sets `status = "done"` when existing videos are found, enabling immediate table + summary rendering
  - Empty/missing transcript index gracefully keeps the normal empty startup state

### Technical Details
`GET /api/transcripts` is defined before `GET /api/transcripts/{video_id}` to avoid FastAPI path matching conflicts. On the frontend, initial-load errors are silently ignored to preserve a resilient empty-state startup when no transcript data exists yet.

---

## Remove Whisper Fallback
**Date**: 2026-04-06
**Plan**: `src/Plans/RemoveWhisper/PLAN.md`

### Summary
Removed the entire Whisper-based fallback transcription system from all three layers (BE, API, FE). YouTube auto-generated captions cover virtually all videos, making the Whisper path unnecessary.

### Changes
- **Files deleted**: `src/whisper_transcriber.py`
- **Files modified**: `src/fetcher.py`, `src/service.py`, `web/api.py`, `requirements.txt`, `.gitignore`, frontend types/components/hook/CSS
- **Key removals**:
  - `faster-whisper` dependency removed from `requirements.txt`
  - `fetch_transcript_with_fallback()` removed from `src/fetcher.py`
  - `whisper_model` parameter removed from service, API, and frontend
  - Whisper toggle/model dropdown removed from FetchForm
  - Whisper-related SSE steps removed (downloading_audio, transcribing, whisper_complete)
  - `.audio_cache/` entry removed from `.gitignore`

### Technical Details
The Whisper path downloaded full audio streams via yt-dlp, which triggered aggressive YouTube rate-limiting (429 errors) after ~10-20 videos. The transcript API is much lighter and sufficient for the use case. Removing Whisper eliminated the `faster-whisper` dependency (~140MB+ model downloads) and simplified the codebase significantly (~57 Whisper references across 13 files).

---

## TopicFilter (LLM Topic Scoring)
**Date**: 2026-04-07
**Plan**: `src/Plans/TopicFilter/PLAN.md`

### Summary
Added a Gemini-powered topic filter that scores each transcript against a free-text topic and streams ranked relevance results to the web UI in real time.

### Changes
- **Files created**: `src/llm_filter.py`, `web/frontend/src/components/TopicFilterPanel.tsx`, `web/frontend/src/components/FilterResultsList.tsx`, `web/frontend/src/hooks/useTopicFilter.ts`
- **Files modified**: `requirements.txt`, `web/api.py`, `web/frontend/src/types.ts`, `web/frontend/src/App.tsx`, `web/frontend/src/App.css`
- **Key additions**:
  - Gemini integration (`gemini-2.0-flash`) with `GEMINI_API_KEY` environment configuration
  - SSE endpoint `POST /api/filter-by-topic` with `filter_start`, `filter_progress`, `filter_done`, and `filter_error` events
  - Topic scoring cache persisted as `transcripts/_filter_cache.json` keyed by `(video_id, normalized_topic)`
  - Topic filter panel (topic input + threshold slider) and ranked results list with AI explanations
  - Frontend streaming hook (`useTopicFilter`) integrated into `App.tsx` with progress and error states

### Technical Details
`src/llm_filter.py` truncates transcript input (`MAX_TRANSCRIPT_CHARS = 12_000`), requests strict JSON output from Gemini, and validates/parses responses with fallback JSON extraction. To stay within free-tier limits, non-cached requests are rate-limited (`REQUEST_DELAY_SECONDS = 4.0`) and cache entries are saved incrementally after each scored video.

---

## Skip Already-Fetched Transcripts
**Date**: 2026-04-07
**Plan**: `src/Plans/SkipCached/PLAN.md`

### Summary
Re-fetching a channel now skips videos whose transcript body is already available locally. Only uncached videos (or previously no-transcript entries) trigger YouTube transcript API calls.

### Changes
- **Files modified**: `src/storage.py`, `src/service.py`, `web/frontend/src/types.ts`, `web/frontend/src/components/VideoProgressList.tsx`, `web/frontend/src/components/VideoTable.tsx`
- **Key additions**:
  - `extract_transcript_body()` in `src/storage.py` to read transcript content from saved Markdown files
  - Cache-aware flow in `src/service.py` with `video_status: "cached"` and `transcript_source: "cached"`
  - API-call pacing now applies only between real YouTube fetches (not cached reads)
  - Post-save `_index.json` merge logic to preserve entries for videos outside the current batch
  - Frontend support for cached state in progress steps and transcript source display (`📦 Cached`)

### Technical Details
Cache hit conditions require all of: indexed `video_id`, `has_transcript: true`, and non-empty extracted Markdown transcript body. If any condition fails, the video is fetched normally. Videos with `has_transcript: false` remain re-fetch candidates.

---
