# BE Developer — Skip Reason Messages + Rate-Limit Short-Circuit

## Goal

Change `fetch_transcript()` to return a structured skip reason when a transcript cannot be fetched. Update the service layer to propagate the reason in SSE events and short-circuit all remaining uncached videos when YouTube rate-limits a request.

## Files

| Action | File |
|--------|------|
| **Modify** | `src/fetcher.py` |
| **Modify** | `src/service.py` |

## Blocked By

Nothing — can start immediately.

## Delivers

- Skipped videos include a human-readable reason in the SSE `"skipped"` event's `error` field
- When YouTube rate-limits one video, all subsequent uncached videos are auto-skipped instantly (no API calls, no sleep)

---

## Detailed Steps

### 1. Modify `src/fetcher.py` — return `(text, reason)` tuple

#### 1a. Update `fetch_transcript()` return type and exception handlers

**Current signature:**
```python
def fetch_transcript(video_id: str, languages: list[str] | None = None) -> str | None:
```

**New signature:**
```python
def fetch_transcript(video_id: str, languages: list[str] | None = None) -> tuple[str | None, str | None]:
```

**Current exception handling:**
```python
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=languages)
        return " ".join(snippet.text for snippet in transcript)
    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
        logger.debug("No transcript for %s: %s", video_id, exc)
        return None
    except (IpBlocked, RequestBlocked) as exc:
        logger.warning("YouTube blocked request for %s: %s", video_id, type(exc).__name__)
        return None
    except Exception as exc:
        logger.warning("Failed to fetch transcript for %s: %s", video_id, exc)
        return None
```

**New exception handling:**
```python
    try:
        ytt_api = YouTubeTranscriptApi()
        transcript = ytt_api.fetch(video_id, languages=languages)
        return " ".join(snippet.text for snippet in transcript), None
    except NoTranscriptFound:
        logger.debug("No transcript for %s: NoTranscriptFound", video_id)
        return None, "No transcript available"
    except TranscriptsDisabled:
        logger.debug("No transcript for %s: TranscriptsDisabled", video_id)
        return None, "Transcripts disabled by uploader"
    except VideoUnavailable:
        logger.debug("No transcript for %s: VideoUnavailable", video_id)
        return None, "Video unavailable"
    except IpBlocked:
        logger.warning("YouTube blocked request for %s: IpBlocked", video_id)
        return None, "YouTube rate limit (IP blocked)"
    except RequestBlocked:
        logger.warning("YouTube blocked request for %s: RequestBlocked", video_id)
        return None, "YouTube rate limit (request blocked)"
    except Exception as exc:
        logger.warning("Failed to fetch transcript for %s: %s", video_id, exc)
        return None, f"Unexpected error: {exc}"
```

Key change: each exception now produces a distinct reason string. `IpBlocked` and `RequestBlocked` reasons start with `"YouTube rate limit"` — this prefix is used by the service layer to detect rate-limiting.

#### 1b. Update `fetch_all_transcripts()` for the new return type

**Current:**
```python
    for i, video in enumerate(videos):
        video.transcript = fetch_transcript(video.video_id, languages=languages)
```

**New:**
```python
    for i, video in enumerate(videos):
        text, _reason = fetch_transcript(video.video_id, languages=languages)
        video.transcript = text
```

The `_reason` is discarded here since the CLI doesn't display skip reasons. This keeps the CLI path unchanged.

### 2. Modify `src/service.py` — propagate reason + rate-limit short-circuit

#### 2a. Initialize `rate_limited` flag

Add `rate_limited = False` next to the existing `last_was_api_call = False` line (before the `for` loop):

```python
    last_was_api_call = False
    rate_limited = False
```

#### 2b. Replace the `if cached_entry is None:` block

**Current:**
```python
        if cached_entry is None:
            if last_was_api_call:
                time.sleep(1.5)

            # Step 1: Check YouTube captions
            yield {"event": "video_status", "video_id": video.video_id, "step": "checking_captions"}

            text = fetch_transcript(video.video_id, languages=[lang])

            if text is not None:
                yield {"event": "video_status", "video_id": video.video_id, "step": "captions_found"}
                video.transcript = text
                transcript_source = "youtube"
            else:
                yield {"event": "video_status", "video_id": video.video_id, "step": "no_captions"}
                yield {"event": "video_status", "video_id": video.video_id, "step": "skipped"}
                video.transcript = None

            last_was_api_call = True
```

**New:**
```python
        if cached_entry is None:
            if rate_limited:
                yield {
                    "event": "video_status",
                    "video_id": video.video_id,
                    "step": "skipped",
                    "error": "Skipped — YouTube rate limited a previous request",
                }
                video.transcript = None
            else:
                if last_was_api_call:
                    time.sleep(1.5)

                yield {"event": "video_status", "video_id": video.video_id, "step": "checking_captions"}

                text, reason = fetch_transcript(video.video_id, languages=[lang])

                if text is not None:
                    yield {"event": "video_status", "video_id": video.video_id, "step": "captions_found"}
                    video.transcript = text
                    transcript_source = "youtube"
                else:
                    yield {"event": "video_status", "video_id": video.video_id, "step": "no_captions"}
                    yield {
                        "event": "video_status",
                        "video_id": video.video_id,
                        "step": "skipped",
                        "error": reason,
                    }
                    video.transcript = None

                    if reason and reason.startswith("YouTube rate limit"):
                        rate_limited = True

                last_was_api_call = True
```

Key behaviors:
- Rate-limited path: no sleep, no API call, `last_was_api_call` not set
- Cached videos unaffected — `cached_entry` check happens before `rate_limited` check
- Progress event still emitted for every video (existing code after this block)

---

## Verification

1. Fetch channel → skipped events include `"error"` with reason string
2. Simulate `IpBlocked` on 2nd video → videos 3+ auto-skipped instantly with rate-limit message
3. Cached videos still show `"cached"` step regardless of rate-limit flag
4. CLI (`fetch_all_transcripts()`) still works — `_reason` is discarded
