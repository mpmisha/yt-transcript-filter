# LLM Topic Filter — Development Plan

## Overview

Add an LLM-powered topic filter that lets users describe a topic of interest (e.g., "indie hacking monetization strategies") and get back a relevance-scored, ranked list of videos from the fetched transcripts. Uses Google Gemini free tier — no cost to operate.

## Motivation

- The existing `filter.py` only supports exact keyword matching — misses semantic intent
- Users want to find all videos about a _concept_, not just videos containing a specific word
- YouTube channels can have hundreds of videos — manually scanning transcripts is impractical
- Google Gemini free tier (15 req/min, 1M tokens/day) is more than sufficient for this use case

## User Flow

```
1. User fetches transcripts for a channel           (existing flow)
2. After fetch completes, user sees "Filter by Topic" panel
3. User types a topic: "bootstrapping a SaaS to $10k MRR"
4. User clicks "Filter" → SSE stream begins
5. Each video is scored by Gemini → progress updates in real-time
6. Results: ranked table with relevance scores (0-10) and AI explanations
7. User can adjust threshold slider to show only highly relevant videos
```

## Architecture

```
FE: TopicFilterPanel ──POST /api/filter-by-topic──▶ API: SSE stream
                                                        │
                                                        ▼
                                                   BE: llm_filter.py
                                                        │
                                                   ┌────┴────┐
                                                   │ Gemini  │
                                                   │  API    │
                                                   └─────────┘
```

## Shared Contract

### API Endpoint

```
POST /api/filter-by-topic
Content-Type: application/json

{
  "topic": "bootstrapping a SaaS business",
  "threshold": 5,
  "output_dir": "./transcripts"
}
```

- `topic` — free-text description of the user's interest (required)
- `threshold` — minimum relevance score 0-10 to include in results (default: 5)
- `output_dir` — transcript directory path (default: `"./transcripts"`)

### SSE Events

**filter_start** — emitted once at the beginning:
```json
{
  "event": "filter_start",
  "total": 10,
  "topic": "bootstrapping a SaaS business"
}
```

**filter_progress** — emitted per video as Gemini returns:
```json
{
  "event": "filter_progress",
  "current": 3,
  "total": 10,
  "video_id": "abc123",
  "title": "How I Built a $10k/mo SaaS",
  "url": "https://www.youtube.com/watch?v=abc123",
  "relevance_score": 9,
  "explanation": "Directly discusses bootstrapping a SaaS from zero to $10k MRR, covering pricing, marketing, and retention strategies.",
  "relevant": true
}
```

- `relevance_score` — integer 0-10 from Gemini
- `explanation` — 1-2 sentence AI explanation of relevance
- `relevant` — boolean, `true` if score >= threshold

**filter_done** — emitted when all videos are processed:
```json
{
  "event": "filter_done",
  "total": 10,
  "relevant_count": 4,
  "topic": "bootstrapping a SaaS business"
}
```

**filter_error** — emitted on unrecoverable error:
```json
{
  "event": "filter_error",
  "detail": "Gemini API key not configured"
}
```

### Gemini Prompt Design

The prompt sends a truncated transcript (first 12,000 characters ≈ 3,000 tokens) to keep costs near zero:

```
You are a content relevance judge. Given a YouTube video transcript and a topic of interest, rate how relevant the video is to the topic.

Topic: {topic}

Transcript (may be truncated):
{transcript_text}

Respond with ONLY a JSON object:
{
  "relevance_score": <integer 0-10>,
  "explanation": "<1-2 sentence explanation>"
}

Scoring guide:
- 0-2: Not relevant at all
- 3-4: Tangentially related
- 5-6: Somewhat relevant, touches on the topic
- 7-8: Clearly relevant, discusses the topic substantially
- 9-10: Highly relevant, the topic is a main focus
```

### Caching Strategy

Results are cached per `(video_id, topic)` in `_filter_cache.json` inside the transcripts directory:

```json
{
  "abc123:bootstrapping a saas business": {
    "relevance_score": 9,
    "explanation": "...",
    "cached_at": "2026-04-06T15:00:00Z"
  }
}
```

Cache key is `{video_id}:{topic_lowercase_stripped}`. Cache is loaded at the start and saved after each video is processed. This avoids re-calling Gemini when the user re-runs the same filter.

## Developer Tasks

Each task MUST be delegated to the correct specialized agent.

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Create the `src/llm_filter.py` module with Gemini integration and the filtering generator.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to create/modify:
- **Create** `src/llm_filter.py` — Gemini client, scoring function, filter generator, caching
- **Modify** `requirements.txt` — add `google-generativeai>=0.8.0`

### Task 2 → Delegate to `@api-developer`

**API Developer**: Add the `/api/filter-by-topic` SSE endpoint.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

Files to modify:
- **Modify** `web/api.py` — new Pydantic model, new SSE endpoint

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: Build the topic filter UI panel, hook, and integrate into the app.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

Files to create/modify:
- **Modify** `web/frontend/src/types.ts` — add filter-related types
- **Create** `web/frontend/src/components/TopicFilterPanel.tsx` — filter input UI
- **Create** `web/frontend/src/components/FilterResultsList.tsx` — ranked results display
- **Create** `web/frontend/src/hooks/useTopicFilter.ts` — SSE hook for filtering
- **Modify** `web/frontend/src/App.tsx` — wire in filter panel after fetch
- **Modify** `web/frontend/src/App.css` — styles for new components

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Task 2 (API Dev)
                            │
Task 3 (FE Dev) ───────────┘ (integration)
```

- **Task 1 and Task 3** can start in parallel
- **Task 2** starts once Task 1 is complete (needs the generator signature)
- **Task 3** UI/types are independent; can be done in parallel with Task 1

## Configuration

The Gemini API key is provided via environment variable:

```bash
export GEMINI_API_KEY="your-key-from-aistudio.google.com"
```

The BE module checks for this at startup and raises a clear error if missing.

## Cost Estimate

| Channel Size | Input Tokens (est.) | Gemini Free Tier Usage |
|-------------|--------------------|-----------------------|
| 10 videos   | ~30k tokens        | 3% of daily limit     |
| 50 videos   | ~150k tokens       | 15% of daily limit    |
| 200 videos  | ~600k tokens       | 60% of daily limit    |

Rate limiting: 15 req/min → a 50-video channel takes ~3.5 minutes. The BE layer adds a 4-second delay between requests to stay well within limits.

## Verification

1. `python3 -c "from src.llm_filter import filter_by_topic; print('OK')"` — no import errors
2. `cd web/frontend && npx tsc --noEmit` — no TypeScript errors
3. `grep -r "GEMINI_API_KEY" src/llm_filter.py` — env var is read properly
4. Start dev servers, fetch a channel, enter a topic, observe SSE progress and ranked results
5. Re-run same filter — should use cached results (no Gemini calls)
