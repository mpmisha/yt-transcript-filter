# yt-transcript-filter

Scrape YouTube channel/playlist transcripts and filter videos by topic — via CLI or Web UI.

## Features

- Fetch transcripts from any YouTube channel or playlist
- **Smart caching** — re-fetching a channel skips videos with already-saved transcript bodies, reducing YouTube API calls
- **Markdown formatting** — transcripts saved as structured Markdown with title, metadata, and paragraphs
- **Real-time progress panel** — per-video step tracking during fetch (checking captions, found/no captions, skipped, cached)
- **Video limit** — optionally cap the number of videos to process (CLI: `--limit`, Web UI: limit input)
- **Transcript viewer** — read transcripts directly in the UI via a modal overlay
- **Default transcript view on load** — app auto-loads existing transcripts at startup (when `transcripts/_index.json` exists)
- Search transcripts by keyword with ranked results and context snippets (CLI)
- Filter videos by include/exclude keywords (CLI)
- **AI Topic Filter (Gemini)** — relevance-scored ranking with SSE progress and cached results per `(video_id, topic)` (Web UI/API)
- Web UI with real-time progress streaming (SSE)
- CLI for scripting and automation

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pip install -r requirements.txt
pip install -r web/requirements.txt
```

For the frontend:
```bash
npm install              # root dependencies (concurrently)
npm run install:fe       # frontend dependencies
```

## CLI Usage

### 1. Fetch transcripts from a channel or playlist

```bash
ytf fetch "https://www.youtube.com/playlist?list=PLxxxxxx" -o ./transcripts
ytf fetch "https://www.youtube.com/@ChannelName/videos" -o ./transcripts
ytf fetch "https://www.youtube.com/@ChannelName/videos" -n 5   # limit to 5 videos
ytf fetch "https://www.youtube.com/@ChannelName/videos" -l en  # transcript language
```

### 2. Search transcripts by keyword

```bash
ytf search "machine learning" "neural network" -d ./transcripts
```

### 3. Filter videos by topic (include/exclude)

```bash
ytf filter -d ./transcripts --include "python" --include "tutorial" --exclude "sponsor"
```

---

## Web UI

A browser-based interface for fetching transcripts with real-time progress. Existing transcripts are auto-loaded on startup. Enter a YouTube channel or playlist URL, click **Fetch**, and watch results populate progressively.

### Architecture

| Layer | Tech | Path |
|-------|------|------|
| **Service** | Python generator wrapping `fetcher` + `storage` | `src/service.py` |
| **API** | FastAPI with SSE streaming | `web/api.py` |
| **Frontend** | React 19 + TypeScript (Vite) | `web/frontend/` |

Communication between frontend and backend uses **Server-Sent Events (SSE)** for real-time progress streaming.

### Running the Web UI

**Option 1 — Single command (recommended):**

```bash
npm run dev
# Starts both API (port 8000) and frontend (port 5173) in parallel
```

**Option 2 — Separate terminals:**

```bash
# Terminal 1: API server
npm run dev:api

# Terminal 2: Frontend
npm run dev:fe
```

Open http://localhost:5173 in your browser.

### Progress Panel

During fetching, the UI shows a real-time progress panel with per-video status tracking:

- All videos appear immediately after discovery (as "Pending")
- Each video updates through steps: Checking captions → Captions found / No captions → Skipped, or directly to Cached when loaded locally
- Active steps show a pulsing animation
- Status icons: ⬜ Pending, ⏳ In progress, ✅ YouTube captions, ⚠️ No captions, ⏭️ Skipped, 📦 Cached
- After completion, the progress panel is replaced by the results table and summary

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/api/fetch-transcripts` | Streams SSE progress events for each video |
| `POST` | `/api/filter-by-topic` | Streams SSE topic-filter events with Gemini relevance scoring |
| `GET` | `/api/transcripts` | Returns saved transcript index data for default table view on app load |
| `GET` | `/api/transcripts/{video_id}` | Returns transcript content as JSON |

**SSE events** for `/api/fetch-transcripts`:

| Event | Description |
|-------|-------------|
| `video_list` | Emitted once with discovered videos before processing starts |
| `video_status` | Per-video step updates (`pending`, `checking_captions`, `captions_found`, `no_captions`, `skipped`, `cached`) |
| `progress` | Emitted per video with row data including `has_transcript` and `transcript_source` |
| `done` | Emitted once at completion with totals |
| `error` | Emitted on validation/runtime errors |

`transcript_source` semantics:

| Value | Meaning |
|-------|---------|
| `"youtube"` | Transcript fetched from YouTube captions API during this run |
| `"cached"` | Transcript loaded from existing local Markdown file (API fetch skipped) |
| `null` | No transcript available for the video |

**Request body** for `/api/fetch-transcripts`:

```json
{
  "url": "https://www.youtube.com/@ChannelName/videos",
  "lang": "en",
  "limit": 10
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | — | YouTube channel or playlist URL |
| `lang` | No | `"en"` | Transcript language code |
| `limit` | No | `null` | Max number of videos to process (`null` for all, must be ≥ 1) |

**Request body** for `/api/filter-by-topic`:

```json
{
  "topic": "bootstrapping a SaaS business",
  "threshold": 5,
  "output_dir": "./transcripts"
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `topic` | Yes | — | Free-text topic to score against transcripts |
| `threshold` | No | `5` | Minimum relevance score to mark a video as relevant (`0-10`) |
| `output_dir` | No | `"./transcripts"` | Transcript directory used for index/transcript/cache files |

**SSE events** for `/api/filter-by-topic`:

| Event | Description |
|-------|-------------|
| `filter_start` | Emitted once with `{ total, topic }` before scoring starts |
| `filter_progress` | Emitted per video with `{ current, total, video_id, title, url, relevance_score, explanation, relevant }` |
| `filter_done` | Emitted once with `{ total, relevant_count, topic }` |
| `filter_error` | Emitted on validation/runtime error with `{ detail }` |

### NPM Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start API + frontend in parallel |
| `npm run dev:api` | Start FastAPI server only |
| `npm run dev:fe` | Start Vite frontend only |
| `npm run build` | Build frontend for production |
| `npm run install:fe` | Install frontend dependencies |

### Project Structure

```
yt-transcript-filter/
├── src/
│   ├── cli.py                 # CLI entry point
│   ├── fetcher.py             # yt-dlp metadata + transcript API integration
│   ├── filter.py              # Keyword filtering
│   ├── llm_filter.py          # Gemini topic scoring + per-topic cache
│   ├── storage.py             # Save/load transcripts (Markdown formatted)
│   ├── service.py             # Generator service layer (web)
│   └── Plans/                 # Feature development plans
│       ├── DefaultView/
│       ├── FetchPanel/
│       ├── Progress/
│       ├── RemoveWhisper/
│       ├── SkipCached/
│       ├── TopicFilter/
│       ├── TranscriptFormatting/
│       ├── TranscriptViewer/
│       ├── VideoLimit/
│       └── Whisper/
├── web/
│   ├── api.py                 # FastAPI SSE endpoints
│   ├── requirements.txt       # Backend web dependencies
│   └── frontend/              # React 19 + TypeScript app
│       └── src/
│           ├── App.tsx
│           ├── types.ts
│           ├── hooks/
│           │   ├── useFetchTranscripts.ts
│           │   └── useTopicFilter.ts
│           └── components/
│               ├── FetchForm.tsx
│               ├── VideoTable.tsx
│               ├── VideoProgressList.tsx
│               ├── TranscriptModal.tsx
│               ├── ProgressBar.tsx
│               ├── SummaryCard.tsx
│               ├── TopicFilterPanel.tsx
│               ├── FilterResultsList.tsx
│               └── ErrorMessage.tsx
├── docs/
│   └── DEVELOPMENT_LOG.md     # Chronological feature development log
├── .env                       # Environment variables (GEMINI_API_KEY) — git-ignored
├── .gitignore
├── package.json               # Root scripts (dev, build)
├── requirements.txt           # Core Python dependencies
└── pyproject.toml
```

## Configuration

- Python dependencies: `requirements.txt`
- Web API dependencies: `web/requirements.txt`
- Frontend dependencies and scripts: `web/frontend/package.json`
- Runtime data directory: `./transcripts` (stores transcript Markdown files + `_index.json`)
- AI topic filtering requires `GEMINI_API_KEY` — set via environment variable:

```bash
export GEMINI_API_KEY="your-key-from-aistudio.google.com"
```

A `.env` file is included in the project root (git-ignored) as a convenient place to store the key. Source it before running:

```bash
# Load .env into your shell
export $(cat .env | xargs)
```

Get a free API key at https://aistudio.google.com/apikey
