# yt-transcript-filter

Scrape YouTube channel/playlist transcripts and filter videos by topic — via CLI or Web UI. When YouTube captions are unavailable, optionally auto-transcribe using local Whisper speech-to-text.

## Features

- Fetch transcripts from any YouTube channel or playlist
- **Whisper fallback** — auto-transcribe videos without captions using local AI (tiny/base/small/medium models)
- **Real-time progress panel** — per-video step tracking during fetch (checking captions, downloading audio, transcribing…)
- **Video limit** — optionally cap the number of videos to process (CLI: `--limit`, Web UI: limit input)
- Search transcripts by keyword with ranked results and context snippets
- Filter videos by topic with include/exclude keywords
- Web UI with real-time progress streaming (SSE)
- CLI for scripting and automation

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
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

A browser-based interface for fetching transcripts with real-time progress. Enter a YouTube channel or playlist URL, optionally enable Whisper for auto-transcription, click **Fetch**, and watch results populate progressively.

### Architecture

| Layer | Tech | Path |
|-------|------|------|
| **Service** | Python generator wrapping `fetcher` + `storage` + `whisper_transcriber` | `src/service.py` |
| **API** | FastAPI with SSE streaming | `web/api.py` |
| **Frontend** | React 19 + TypeScript + Tailwind CSS (Vite) | `web/frontend/` |

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
- Each video updates through steps: Checking captions → Captions found / No captions → Downloading audio → Transcribing → Complete
- Active steps show a pulsing animation
- Status icons: ⬜ Pending, ⏳ In progress, ✅ YouTube captions, 🎤 Whisper, ❌ Failed, ⏭️ Skipped
- After completion, the progress panel is replaced by the results table and summary

### Whisper Auto-Transcription

When YouTube captions are unavailable, Whisper can transcribe videos locally from audio:

1. Toggle **"Auto-transcribe with Whisper"** in the UI
2. Select a model size:

| Model | Size | Quality | Speed |
|-------|------|---------|-------|
| Tiny | ~75MB | Basic | Fastest |
| Base | ~140MB | Decent | Fast |
| Small | ~460MB | Good | Moderate |
| Medium | ~1.5GB | Very good | Slower |

3. The model downloads automatically on first use
4. Audio files are cleaned up after transcription
5. The results table shows the transcript source (YouTube / Whisper / None)

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check — returns `{"status": "ok"}` |
| `POST` | `/api/fetch-transcripts` | Streams SSE progress events for each video |

**Request body** for `/api/fetch-transcripts`:

```json
{
  "url": "https://www.youtube.com/@ChannelName/videos",
  "lang": "en",
  "whisper_model": "base",
  "limit": 10
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `url` | Yes | — | YouTube channel or playlist URL |
| `lang` | No | `"en"` | Transcript language code |
| `whisper_model` | No | `null` | Whisper model size (`"tiny"`, `"base"`, `"small"`, `"medium"`, or `null` to disable) |
| `limit` | No | `null` | Max number of videos to process (`null` for all, must be ≥ 1) |

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
│   ├── fetcher.py             # yt-dlp + transcript API + fallback
│   ├── filter.py              # Keyword filtering
│   ├── storage.py             # Save/load transcripts
│   ├── service.py             # Generator service layer (web)
│   ├── whisper_transcriber.py # Audio download + Whisper transcription
│   └── Plans/                 # Development plans per feature
│       ├── FetchPanel/        # ✅ V1 fetch panel (completed)
│       ├── Whisper/           # ✅ Whisper fallback (completed)
│       ├── Progress/          # ✅ Per-video progress panel (completed)
│       └── VideoLimit/        # ✅ Video limit input (completed)
├── web/
│   ├── api.py                 # FastAPI SSE endpoints
│   ├── requirements.txt       # Backend web dependencies
│   └── frontend/              # React 19 + TypeScript + Tailwind app
│       └── src/
│           ├── App.tsx
│           ├── types.ts
│           ├── hooks/
│           │   └── useFetchTranscripts.ts
│           └── components/
│               ├── FetchForm.tsx
│               ├── VideoTable.tsx
│               ├── VideoProgressList.tsx
│               ├── ProgressBar.tsx
│               ├── SummaryCard.tsx
│               └── ErrorMessage.tsx
├── package.json               # Root scripts (dev, build)
├── requirements.txt           # Core Python dependencies
└── pyproject.toml
```
