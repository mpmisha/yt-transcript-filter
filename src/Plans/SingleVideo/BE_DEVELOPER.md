# BE Developer — Single Video URL Support

## Goal

Ensure `get_video_list()` works correctly for single YouTube video URLs. If `yt-dlp --flat-playlist` returns incomplete metadata for single videos, add detection and a fallback code path.

## Files

| Action | File |
|--------|------|
| **Modify** (if needed) | `src/fetcher.py` |

## Blocked By

Nothing — can start immediately.

## Delivers

Users can paste a single video URL and get the same transcript fetch experience as a channel/playlist.

---

## Detailed Steps

### Step 0: Verify current behavior (before writing any code)

Run this in the terminal with the virtualenv activated:

```bash
yt-dlp --flat-playlist --dump-json --no-warnings "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 2>/dev/null | python3 -m json.tool
```

Check the output for:
- `id` — should be present
- `title` — may be `None` or `"[Private video]"` with `--flat-playlist`
- `duration` — may be `None`
- `upload_date` — may be `None`

**If all fields are populated**: No code changes needed. Stop here.

**If `title`/`duration` are missing**: Proceed to Step 1.

### Step 1: Add `_is_single_video_url()` helper

Add after the `VideoInfo` dataclass:

```python
import re
from urllib.parse import parse_qs, urlparse

def _is_single_video_url(url: str) -> bool:
    """Return True if the URL points to a single YouTube video."""
    parsed = urlparse(url)
    if parsed.hostname in ("youtu.be", "www.youtu.be"):
        return True
    if parsed.hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if parsed.path == "/watch" and "v" in parse_qs(parsed.query):
            return True
        if re.match(r"^/shorts/[\w-]+$", parsed.path):
            return True
    return False
```

This detects:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID` (treat as single video)
- `https://youtu.be/VIDEO_ID`
- `https://www.youtube.com/shorts/VIDEO_ID`

### Step 2: Update `get_video_list()` to handle single videos

**Current:**
```python
def get_video_list(channel_or_playlist_url: str) -> list[VideoInfo]:
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--no-warnings",
        channel_or_playlist_url,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
```

**New:**
```python
def get_video_list(channel_or_playlist_url: str) -> list[VideoInfo]:
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--no-warnings",
    ]

    if not _is_single_video_url(channel_or_playlist_url):
        cmd.append("--flat-playlist")

    cmd.append(channel_or_playlist_url)

    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
```

For single videos, omitting `--flat-playlist` makes yt-dlp fetch the full video page, ensuring `title`, `duration`, and `upload_date` are populated. For channels/playlists, `--flat-playlist` is kept to avoid downloading every video page.

### Step 3: Add imports (only if Step 1 is needed)

Add to the import block at the top of `src/fetcher.py`:

```python
import re
from urllib.parse import parse_qs, urlparse
```

---

## What NOT to Change

- **`src/service.py`** — No changes. It processes whatever `get_video_list()` returns.
- **`web/api.py`** — No changes. SSE events are the same.
- **Frontend** — No changes. The input field already accepts any URL.

---

## Verification

1. `yt-dlp --dump-json --no-warnings "https://www.youtube.com/watch?v=VIDEO_ID"` → returns full metadata with title, duration, upload_date
2. Run `npm run dev`, paste a single video URL, click Fetch → one video appears, transcript fetched
3. Paste `https://youtu.be/VIDEO_ID` → same behavior
4. Paste a channel URL → still works (uses `--flat-playlist`)
5. Paste `https://www.youtube.com/watch?v=VIDEO_ID&list=PLAYLIST_ID` → fetches only the single video
6. Existing tests still pass
