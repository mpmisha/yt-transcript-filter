# Markdown Transcript Formatting — Development Plan

## Overview

Integrate automatic Markdown formatting into the transcript save pipeline. When transcripts are saved to disk, they are formatted as structured Markdown with a title, metadata header, and paragraphs split on `>>` speaker-change markers — instead of a single long line of raw text.

## Motivation

- Raw transcripts are saved as a single unbroken line — unreadable in any editor
- YouTube auto-generated transcripts include `>>` markers at speaker changes, providing natural paragraph break points
- Markdown is human-readable, renders nicely in GitHub/VS Code, and supports metadata headers

## Architecture Change

```
Current:  transcript text → write raw text to .txt file
New:      transcript text → format_transcript_as_markdown() → write formatted Markdown to .md file
```

The formatter is a pure function in `src/storage.py` — no new modules, no external dependencies.

## Developer Tasks

### Task 1 → Delegate to `@be-developer`

**BE Developer**: Add the Markdown formatter function and update `save_transcripts()` to use it.

Full specification: [BE_DEVELOPER.md](BE_DEVELOPER.md)

Files to modify:
- **Modify** `src/storage.py` — add `format_transcript_as_markdown()`, update `save_transcripts()` to use `.md` extension and formatted content

### Task 2 → Delegate to `@api-developer`

**API Developer**: No changes needed.

Full specification: [API_DEVELOPER.md](API_DEVELOPER.md)

### Task 3 → Delegate to `@fe-developer`

**FE Developer**: No changes needed.

Full specification: [FE_DEVELOPER.md](FE_DEVELOPER.md)

### Task 4 → Delegate to `@documentation`

**Documentation Agent**: After Tasks 1–3 are complete, update project documentation.

Trigger: `@documentation` — update README.md, docs/DEVELOPMENT_LOG.md, and web/frontend/README.md to reflect:
- Transcript output format changed from `.txt` to `.md`
- New `format_transcript_as_markdown()` function in `src/storage.py`
- Updated project structure (`.md` files in `transcripts/`)

## Dependency Graph

```
Task 1 (BE Dev) ──▶ Task 4 (Documentation)
Task 2 (API Dev) — no changes
Task 3 (FE Dev) — no changes
```

- Only **Task 1** requires code changes
- **Task 4** (Documentation) runs after Task 1 is complete

## Shared Contract

### Transcript File Format (new)

**Filename**: `{sanitized_title}__{video_id}.md`

**Content structure**:
```markdown
# {Video Title}

**Video:** https://www.youtube.com/watch?v={video_id}
**Video ID:** {video_id}
**Upload Date:** {YYYY-MM-DD or "Unknown"}
**Duration:** {M:SS or "Unknown"}

---

{Paragraph 1 — text before first >>}

{Paragraph 2 — text between first and second >>}

{Paragraph 3 — etc.}
```

### Index File (`_index.json`)

The `file` field in each index entry changes from `.txt` to `.md`:
```json
{
  "video_id": "rGLXc1GmsaI",
  "title": "This App Makes $35K/Month With One Influencer",
  "file": "This App Makes $35K_Month With One Influencer__rGLXc1GmsaI.md"
}
```

## Verification

1. Run a fetch via the UI with limit=1 — verify `.md` file created in `transcripts/`
2. Open the `.md` file — verify it has title, metadata, and paragraphs
3. Verify `_index.json` references `.md` filename
4. Verify no `.txt` files are created for new fetches
5. Existing `.txt` files in `transcripts/` are unchanged (no retroactive conversion)
