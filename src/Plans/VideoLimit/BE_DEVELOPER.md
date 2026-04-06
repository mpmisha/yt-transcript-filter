# BE Developer — Video Limit

## Goal

Add a `limit` parameter to the service layer and CLI so users can cap the number of videos processed. The limit is applied by slicing the video list after discovery.

## Files

| Action | File |
|--------|------|
| **Modify** | `src/service.py` — add `limit` param, slice videos after `get_video_list()` |
| **Modify** | `src/cli.py` — add `--limit` / `-n` click option |

## Blocked By

Nothing — can start immediately.

## Delivers

Updated service generator and CLI that respect an optional video limit.

---

## Detailed Steps

### 1. Modify `src/service.py`

#### Update function signature

Current:
```python
def fetch_channel_transcripts(url: str, lang: str = "en", whisper_model: str | None = None) -> Generator[dict, None, None]:
```

New:
```python
def fetch_channel_transcripts(
    url: str,
    lang: str = "en",
    whisper_model: str | None = None,
    limit: int | None = None,
) -> Generator[dict, None, None]:
```

#### Update docstring

Add to Args:
```python
        limit: Optional max number of videos to process. None means all.
```

#### Slice videos after discovery

After `videos = get_video_list(url)`, add:

```python
    videos = get_video_list(url)

    if limit is not None:
        videos = videos[:limit]

    total = len(videos)
```

This ensures:
- `total` reflects the limited count
- The `video_list` event only contains the limited videos
- All downstream processing (loop, `done` event) uses the sliced list
- No other changes needed — everything downstream uses `videos` and `total`

### 2. Modify `src/cli.py`

#### Add click option to `fetch` command

Current:
```python
@cli.command()
@click.argument("url")
@click.option("--output", "-o", default="./transcripts", help="Output directory for transcripts.")
@click.option("--lang", "-l", default="en", help="Transcript language (default: en).")
def fetch(url: str, output: str, lang: str):
```

New:
```python
@cli.command()
@click.argument("url")
@click.option("--output", "-o", default="./transcripts", help="Output directory for transcripts.")
@click.option("--lang", "-l", default="en", help="Transcript language (default: en).")
@click.option("--limit", "-n", default=None, type=int, help="Max number of videos to fetch.")
def fetch(url: str, output: str, lang: str, limit: int | None):
```

#### Slice video list after fetching

Current:
```python
    with console.status("Getting video list..."):
        videos = get_video_list(url)

    console.print(f"[green]Found {len(videos)} videos.[/]\n")
```

New:
```python
    with console.status("Getting video list..."):
        videos = get_video_list(url)

    if limit is not None:
        videos = videos[:limit]
        console.print(f"[green]Found {len(videos)} videos (limited to {limit}).[/]\n")
    else:
        console.print(f"[green]Found {len(videos)} videos.[/]\n")
```

---

## What NOT to Change

- `src/fetcher.py` — no changes needed. `get_video_list()` always returns all videos; slicing is done by the caller.
- `src/storage.py` — no changes needed.
- `src/whisper_transcriber.py` — no changes needed.

---

## Verification

1. **Service with limit**: Call `fetch_channel_transcripts(url, limit=3)` → generator yields `video_list` with 3 videos, processes only 3, `done` event has `total: 3`
2. **Service without limit**: Call `fetch_channel_transcripts(url)` → same behavior as before (all videos)
3. **Service with limit > total videos**: `limit=100` on a 5-video playlist → processes all 5 (slice is safe on shorter lists)
4. **CLI with limit**: `ytf fetch "URL" -n 3` → "Found N videos (limited to 3)" message, processes 3
5. **CLI without limit**: `ytf fetch "URL"` → unchanged behavior

## Definition of Done

- [ ] `fetch_channel_transcripts()` accepts `limit: int | None = None`
- [ ] Videos are sliced to `[:limit]` after `get_video_list()` when limit is provided
- [ ] `video_list` event reflects the limited count and limited video list
- [ ] `done` event `total` matches the limited count
- [ ] CLI `fetch` command accepts `--limit` / `-n` option
- [ ] CLI prints "(limited to N)" when limit is active
- [ ] No changes to `fetcher.py`, `storage.py`, or `whisper_transcriber.py`
