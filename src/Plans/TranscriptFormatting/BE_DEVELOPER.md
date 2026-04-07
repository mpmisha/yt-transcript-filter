# BE Developer — Markdown Transcript Formatting

## Goal

Add a `format_transcript_as_markdown()` function to `src/storage.py` and update `save_transcripts()` to save formatted Markdown files (`.md`) instead of raw text (`.txt`).

## Files

| Action | File |
|--------|------|
| **Modify** | `src/storage.py` |

## Blocked By

Nothing — can start immediately.

## Delivers

Transcripts saved as structured Markdown with title, metadata, and paragraphs. The `_index.json` references `.md` filenames.

---

## Detailed Steps

### 1. Add `format_transcript_as_markdown()` function

Add this function to `src/storage.py`, above `save_transcripts()`:

```python
def _format_duration(seconds: int | None) -> str:
    """Format duration in seconds as M:SS."""
    if seconds is None:
        return "Unknown"
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


def _format_upload_date(date_str: str | None) -> str:
    """Format YYYYMMDD as YYYY-MM-DD."""
    if not date_str:
        return "Unknown"
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return date_str


def format_transcript_as_markdown(video: VideoInfo) -> str:
    """Format a transcript as a Markdown document with title, metadata, and paragraphs.

    Speaker changes marked by '>>' in the raw transcript are used as paragraph breaks.
    """
    lines = [
        f"# {video.title}",
        "",
        f"**Video:** https://www.youtube.com/watch?v={video.video_id}",
        f"**Video ID:** {video.video_id}",
        f"**Upload Date:** {_format_upload_date(video.upload_date)}",
        f"**Duration:** {_format_duration(video.duration)}",
        "",
        "---",
        "",
    ]

    if video.transcript:
        paragraphs = video.transcript.split(">>")
        for paragraph in paragraphs:
            text = paragraph.strip()
            if text:
                lines.append(text)
                lines.append("")

    return "\n".join(lines)
```

Key design decisions:
- Private helpers `_format_duration` and `_format_upload_date` handle the formatting of metadata fields
- `>>` is consumed (removed) during splitting — it does not appear in the output
- Empty paragraphs from splitting are filtered out
- Each paragraph is separated by a blank line (standard Markdown)
- The function takes a `VideoInfo` object (not raw text) so it can access all metadata

### 2. Update `save_transcripts()` to use the formatter

#### 2a. Change file extension from `.txt` to `.md`

**Before:**
```python
filename = f"{safe_name}__{video.video_id}.txt"
```

**After:**
```python
filename = f"{safe_name}__{video.video_id}.md"
```

#### 2b. Use the formatter for content

**Before:**
```python
if video.transcript:
    filepath.write_text(video.transcript, encoding="utf-8")
else:
    filepath.write_text("[No transcript available]", encoding="utf-8")
```

**After:**
```python
content = format_transcript_as_markdown(video)
filepath.write_text(content, encoding="utf-8")
```

This handles both cases — when transcript exists (formatted with paragraphs) and when it doesn't (the `format_transcript_as_markdown` function will produce a header with no paragraphs, which is cleaner than `[No transcript available]`).

### 3. No changes to `load_transcript()` or `load_index()`

These functions use filenames from `_index.json`, so they automatically work with `.md` filenames. No changes needed.

---

## Expected Final State

### `src/storage.py` — Updated `save_transcripts()` (relevant section)

```python
for video in videos:
    safe_name = sanitize_filename(video.title)
    filename = f"{safe_name}__{video.video_id}.md"
    filepath = output_dir / filename

    content = format_transcript_as_markdown(video)
    filepath.write_text(content, encoding="utf-8")

    index.append({
        "video_id": video.video_id,
        "title": video.title,
        "url": video.url,
        "duration": video.duration,
        "upload_date": video.upload_date,
        "has_transcript": video.transcript is not None,
        "file": filename,
    })
```

### Example output file

For a video titled "This App Makes $35K/Month With One Influencer":

```markdown
# This App Makes $35K/Month With One Influencer

**Video:** https://www.youtube.com/watch?v=rGLXc1GmsaI
**Video ID:** rGLXc1GmsaI
**Upload Date:** 2026-03-15
**Duration:** 24:30

---

Right now, it's easier than ever to build apps, but distribution is harder than it's ever been. Tik Tok, paid ads, Reddit. What do you do? Well, today I think I found the solution.

I partnered with one guy and we grew by 10,000%.

This is Flo, a solo developer who built a really simple mobile app. But for over a year, he tried everything and barely made a few hundred. I tried doing it all by myself and only made $300 per month.

Then something happened that changed everything.
```

---

## Verification

1. Run a fetch via the UI with limit=1 — verify `.md` file created in `transcripts/`
2. Open the `.md` file in VS Code — verify Markdown renders with title, metadata block, and paragraphs
3. Verify `_index.json` references `.md` filename
4. `python3 -c "from src.storage import format_transcript_as_markdown; print('OK')"` — no import errors
5. Verify no `.txt` files are created for new fetches
