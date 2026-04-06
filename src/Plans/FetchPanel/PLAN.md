> **Status: ✅ COMPLETED**

# Fetch Panel Web UI (V1) — Development Plan

## Overview

Add a web UI to the existing `yt-transcript-filter` CLI tool. The first feature is a **Fetch Panel**: the user enters a YouTube channel/playlist URL, clicks Fetch, and sees a table of results populate progressively as transcripts are downloaded.

### Architecture

- **Backend**: FastAPI server (`web/api.py`) wrapping existing Python modules via a service layer (`src/service.py`)
- **Frontend**: React + TypeScript (Vite) in `web/frontend/`
- **Communication**: Server-Sent Events (SSE) for real-time progress streaming

### Developer Roles

| Role | Scope | Files | Detailed Plan |
|------|-------|-------|---------------|
| **BE Developer** | Python service layer (generator wrapping existing modules) | `src/service.py` | [BE_DEVELOPER.md](BE_DEVELOPER.md) |
| **API Developer** | FastAPI HTTP endpoints + SSE streaming | `web/api.py`, `web/requirements.txt` | [API_DEVELOPER.md](API_DEVELOPER.md) |
| **FE Developer** | React app — scaffold, components, SSE hook, integration | `web/frontend/` | [FE_DEVELOPER.md](FE_DEVELOPER.md) |

### Dependency Graph

```
BE Dev (service layer) ──▶ API Dev (FastAPI endpoints)
                                       │
FE Dev (React app) ────────────────────┘ (integration)
```

- **BE Dev** and **FE Dev** start in parallel (no dependencies)
- **API Dev** starts once BE Dev delivers `src/service.py`
- **FE Dev** integrates once API Dev delivers working endpoints (but builds all UI with mock data first)

---

## Shared Contract

All three developers must agree on this contract before starting.

### API Endpoint

```
POST /api/fetch-transcripts
Content-Type: application/json

{
  "url": "https://www.youtube.com/@ChannelName/videos",
  "lang": "en"
}
```

**Response**: `200 OK` with `Content-Type: text/event-stream`

### SSE Event Format

Each event is a JSON object on a single line, prefixed with `data: ` and followed by two newlines:

**Progress event** (emitted once per video):
```
data: {"event":"progress","current":1,"total":5,"video_id":"dQw4w9WgXcQ","title":"Video Title","duration":180,"upload_date":"20240115","url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","has_transcript":true}

```

**Done event** (emitted once at the end):
```
data: {"event":"done","total":5,"with_transcript":3,"output_dir":"./transcripts"}

```

### Error Responses

| Status | Condition | Body |
|--------|-----------|------|
| `400` | Empty URL or invalid lang | `{"detail": "URL is required"}` |
| `500` | Unexpected server error | `{"detail": "Internal server error"}` |

### TypeScript Types

```typescript
interface VideoInfo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  upload_date: string | null;
  has_transcript: boolean;
}

interface FetchProgress {
  current: number;
  total: number;
}

type FetchStatus = "idle" | "loading" | "done" | "error";
```

---

## How to Run (Development)

### Backend
```bash
pip install -r web/requirements.txt
uvicorn web.api:app --reload --port 8000
```

### Frontend
```bash
cd web/frontend
npm install
npm run dev
# Opens at http://localhost:5173, proxies /api to localhost:8000
```

---

## End-to-End Verification

1. Start backend (`uvicorn`) and frontend (`npm run dev`)
2. Enter a small playlist URL (3–5 videos) in the UI
3. Click **Fetch**
4. Confirm: progress bar advances, table rows appear progressively
5. Confirm: summary card shows "X / Y videos have transcripts"
6. Confirm: `./transcripts/_index.json` is written to disk
7. Confirm: videos without captions show ❌ in the table
