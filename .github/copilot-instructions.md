# Project Guidelines

## Architecture

This project has three layers:

| Layer | Language/Stack | Location | Purpose |
|-------|---------------|----------|---------|
| **BE** (Backend) | Python 3.9+ | `src/` | Core logic — YouTube scraping, transcript fetching, filtering, storage |
| **API** | Python + FastAPI | `web/api/` | HTTP layer — FastAPI server exposing BE functionality via REST + SSE |
| **FE** (Frontend) | React 19 + TypeScript + Tailwind CSS | `web/frontend/` | Web UI — single-page app consuming the API |

See `src/Plans/` for development plans organized by task (FetchPanel, Whisper, Progress).

---

## Frontend (React 19 + TypeScript + Tailwind)

### Stack
- **React 19** with functional components only — no class components
- **TypeScript** in strict mode — no `any` types, no `@ts-ignore`
- **Tailwind CSS** for all styling — no CSS modules, no styled-components, no inline `style` props
- **Vite** as the build tool

### Conventions
- Use named exports, not default exports
- One component per file, filename matches component name: `VideoTable.tsx` exports `VideoTable`
- Props interfaces named `{Component}Props`: `VideoTableProps`
- Use React hooks (`useState`, `useCallback`, `useMemo`, `useEffect`) — no external state libraries unless explicitly discussed
- Custom hooks go in `src/hooks/` and start with `use`: `useFetchTranscripts.ts`
- Shared types go in `src/types.ts`
- Utility/helper functions go in `src/utils.ts`
- Prefer `const` arrow functions for components:
  ```tsx
  export const VideoTable = ({ videos }: VideoTableProps) => { ... };
  ```
- Event handlers named `handle{Event}`: `handleSubmit`, `handleClick`
- Callback props named `on{Event}`: `onSubmit`, `onClick`

### Tailwind
- Use Tailwind utility classes directly in JSX — no `@apply` in CSS files
- For repeated class combinations, extract to a component — not to a CSS class
- Use responsive prefixes (`sm:`, `md:`, `lg:`) for responsive design
- Dark mode: use `dark:` prefix if adding dark mode support

---

## API Layer (Python + FastAPI)

### Stack
- **FastAPI** with **Pydantic** for request/response validation
- **Uvicorn** as the ASGI server
- Dependencies in `web/requirements.txt`

### Conventions
- Endpoints prefixed with `/api/`: `/api/health`, `/api/fetch-transcripts`
- Use `async def` for route handlers
- Validate request bodies with **Pydantic models** — not manual dict checks
- Return consistent error responses: `{"detail": "message"}` with appropriate HTTP status codes
- Keep route handlers thin — delegate to service functions in `src/`
- Environment config via `os.environ` — no hardcoded ports or URLs
- Use **CORS middleware** to allow the frontend dev server origin
- Follow the same Python conventions as the BE layer (type hints, PEP 8, etc.)

### SSE (Server-Sent Events)
- Use `StreamingResponse` with `media_type="text/event-stream"`
- Each event formatted as `data: {json}\n\n`
- Include error events in the stream for failures during processing

---

## Backend (Python)

### Stack
- **Python 3.9+** — compatible with 3.9 minimum, use modern syntax where supported
- Dependencies managed in `pyproject.toml` and `requirements.txt`

### Code Style
- Follow **PEP 8** — 4 spaces indentation, snake_case for functions/variables, PascalCase for classes
- Use **type hints** on all function signatures (parameters and return types):
  ```python
  def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
  ```
- Use `from __future__ import annotations` at the top of every module for forward-reference support
- Use **dataclasses** for data structures — not plain dicts or namedtuples:
  ```python
  @dataclass
  class VideoInfo:
      video_id: str
      title: str
  ```
- Use **f-strings** for string formatting — not `.format()` or `%`
- Use **pathlib.Path** for file system operations — not `os.path`

### Error Handling
- Raise specific exceptions with descriptive messages — not bare `raise Exception()`
- Use `try/except` for expected failure points (network calls, file I/O, subprocess) — not for flow control
- Catch the most specific exception type possible — never bare `except:`
- Log the original exception when re-raising: `raise ValueError("msg") from e`

### Structure
- Keep modules focused: one responsibility per file
- Public API at the top, private helpers (prefixed `_`) below
- Imports organized: stdlib → third-party → local, separated by blank lines
- Use **generators** (`yield`) for streaming/iterating large datasets instead of building full lists in memory

### Testing
- Use **pytest** for tests
- Test files named `test_{module}.py` in a `tests/` directory
- Use descriptive test names: `test_fetch_transcript_returns_none_for_unavailable_video`

---

## General (All Languages)

- No commented-out code — delete it, version control has history
- No TODO comments without a linked issue or task
- Keep functions short and focused — if a function needs a comment explaining a section, extract that section
- Prefer early returns over deep nesting
- Variable names should be descriptive — no single letters except in comprehensions/lambdas (`for v in videos`)
