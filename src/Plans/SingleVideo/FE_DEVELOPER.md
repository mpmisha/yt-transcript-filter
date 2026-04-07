# FE Developer — Single Video URL Support

## Goal

No changes needed for the frontend.

## Rationale

The fetch input field already accepts any URL string. The backend handles both single video and channel/playlist URLs. The SSE event sequence is identical — `video_list` with `total: 1`, followed by the normal `video_status` / `progress` / `done` events.

## Files

No files to modify.

## Verification

1. Paste a single video URL, click Fetch → progress list shows one video, processes normally
2. Paste a channel URL → works as before (no regression)
