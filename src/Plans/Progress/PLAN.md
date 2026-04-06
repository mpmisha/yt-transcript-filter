> **Status: ✅ COMPLETED**

# Detailed Progress Panel — Development Plan

## Overview

Add real-time per-video step tracking to the fetch pipeline. Currently the UI shows nothing while a video is being processed (especially slow for Whisper). This feature introduces sub-step SSE events so the UI can show exactly what's happening for each video: checking captions, downloading audio, transcribing, etc.

## What Changes

| Current Behavior | New Behavior |
|-----------------|--------------|
| One `progress` event per video, after all work is done | Sub-step `video_status` events during processing + `progress` event at completion |
| No visibility into Whisper steps | Real-time step labels: downloading audio, transcribing |
| No video list until first video completes | `video_list` event immediately after discovery — all videos shown as "pending" |
| Single overall progress bar | Overall progress bar + per-video status list with step details |

## New SSE Events

### `video_list` — emitted once, right after video discovery

```
data: {"event":"video_list","total":15,"videos":[{"video_id":"abc","title":"...","duration":180,"upload_date":"20240115","url":"https://..."},{"video_id":"def","title":"..."}]}
```

### `video_status` — emitted during processing of each video

```
data: {"event":"video_status","video_id":"abc","step":"checking_captions"}
data: {"event":"video_status","video_id":"abc","step":"captions_found"}
```

Or for Whisper fallback:
```
data: {"event":"video_status","video_id":"def","step":"checking_captions"}
data: {"event":"video_status","video_id":"def","step":"no_captions"}
data: {"event":"video_status","video_id":"def","step":"downloading_audio"}
data: {"event":"video_status","video_id":"def","step":"transcribing"}
data: {"event":"video_status","video_id":"def","step":"whisper_complete"}
```

### Step Values

| Step | Meaning | When |
|------|---------|------|
| `checking_captions` | Trying YouTube transcript API | Always (first step for every video) |
| `captions_found` | YouTube captions available | YouTube has captions |
| `no_captions` | No YouTube captions | YouTube has no captions |
| `downloading_audio` | yt-dlp downloading audio | Whisper enabled + no captions |
| `transcribing` | Whisper model running | Audio downloaded, model processing |
| `whisper_complete` | Whisper transcription done | Whisper succeeded |
| `whisper_failed` | Whisper transcription failed | Whisper error |
| `skipped` | No captions, Whisper disabled | No captions + Whisper off |

### Existing events (unchanged)

- `progress` — still emitted after each video completes (same fields as today)
- `done` — still emitted at the end
- `error` — still emitted on fatal errors

## Full SSE Stream Example

```
data: {"event":"video_list","total":3,"videos":[{"video_id":"a1","title":"Intro","duration":120,"upload_date":"20240115","url":"https://..."},{"video_id":"b2","title":"Deep Dive","duration":600,"upload_date":"20240220","url":"https://..."},{"video_id":"c3","title":"Q&A","duration":1800,"upload_date":"20240310","url":"https://..."}]}

data: {"event":"video_status","video_id":"a1","step":"checking_captions"}
data: {"event":"video_status","video_id":"a1","step":"captions_found"}
data: {"event":"progress","current":1,"total":3,"video_id":"a1","title":"Intro","duration":120,"upload_date":"20240115","url":"https://...","has_transcript":true,"transcript_source":"youtube"}

data: {"event":"video_status","video_id":"b2","step":"checking_captions"}
data: {"event":"video_status","video_id":"b2","step":"no_captions"}
data: {"event":"video_status","video_id":"b2","step":"downloading_audio"}
data: {"event":"video_status","video_id":"b2","step":"transcribing"}
data: {"event":"video_status","video_id":"b2","step":"whisper_complete"}
data: {"event":"progress","current":2,"total":3,"video_id":"b2","title":"Deep Dive","duration":600,"upload_date":"20240220","url":"https://...","has_transcript":true,"transcript_source":"whisper"}

data: {"event":"video_status","video_id":"c3","step":"checking_captions"}
data: {"event":"video_status","video_id":"c3","step":"no_captions"}
data: {"event":"video_status","video_id":"c3","step":"skipped"}
data: {"event":"progress","current":3,"total":3,"video_id":"c3","title":"Q&A","duration":1800,"upload_date":"20240310","url":"https://...","has_transcript":false,"transcript_source":null}

data: {"event":"done","total":3,"with_transcript":2,"with_whisper":1,"output_dir":"./transcripts"}
```

## Developer Tasks

Each task MUST be delegated to the correct specialized agent.

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Add sub-step yielding to the service pipeline and status callbacks to fetcher/whisper modules.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Modify** `src/service.py` — yield `video_list` event after discovery, yield `video_status` events during processing
- **Modify** `src/fetcher.py` — add `status_callback` param to `fetch_transcript_with_fallback()`
- **Modify** `src/whisper_transcriber.py` — add `status_callback` param to `whisper_transcript()`

### Task 2 → Delegate to `@api-developer`

**API Developer**: No code changes required. The existing `StreamingResponse` already forwards all yielded dicts as SSE events. Just verify the new events stream correctly.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- None (verification only)

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Add new types, handle new SSE events in the hook, build the `VideoProgressList` component, update `App.tsx` layout.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to modify:
- **Modify** `web/frontend/src/types.ts` — add `VideoStep`, `SSEVideoListEvent`, `SSEVideoStatusEvent`, `VideoProgressItem`
- **Modify** `web/frontend/src/hooks/useFetchTranscripts.ts` — handle `video_list` and `video_status` events, maintain per-video state map
- **Create** `web/frontend/src/components/VideoProgressList.tsx` — per-video status list with step details
- **Modify** `web/frontend/src/App.tsx` — add `VideoProgressList` during loading, update layout

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Task 2 (API Dev — verify only)
                            │
Task 3 (FE Dev) ────────────┘ (integration)
```

- **Task 1 and Task 3** can start in parallel
- **Task 2** is verification only, runs after Task 1
- **Task 3** UI work is independent (mock data); integration needs Task 1

## UI Layout (during loading)

```
┌─────────────────────────────────────────────────────────┐
│  Found 15 videos                                        │
│  Overall: ████████░░░░░░░░░  3 / 15 videos (20%)       │
├─────────────────────────────────────────────────────────┤
│  1. ✅ Intro to Python          YouTube captions         │
│  2. 🎤 Advanced React           Whisper (complete)       │
│  3. ⏳ Live Q&A                  Transcribing...         │
│  4. ⬜ State Management          Pending                 │
│  5. ⬜ Testing Basics            Pending                 │
│  ...                                                     │
└─────────────────────────────────────────────────────────┘
```

After completion, the `VideoTable` replaces `VideoProgressList` (same as today).

## Verification

1. Fetch with Whisper **disabled** → `video_list` shows all videos as pending, each gets `checking_captions` → `captions_found` or `no_captions` → `skipped`, overall progress bar advances
2. Fetch with Whisper **enabled** → videos without captions show `downloading_audio` → `transcribing` → `whisper_complete` steps
3. Whisper failure → video shows `whisper_failed` step, then `progress` with `has_transcript: false`
4. Large channel → `video_list` event appears immediately, all videos shown as pending before any processing starts
5. Overall progress bar matches completed video count
6. After `done` event, `VideoProgressList` is replaced by `VideoTable` + `SummaryCard`
