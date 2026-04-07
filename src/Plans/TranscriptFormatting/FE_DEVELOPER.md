# FE Developer — Markdown Transcript Formatting

## Goal

No changes needed for the frontend.

## Rationale

The frontend displays video metadata and transcript status from SSE events. It does not read, render, or link to the saved transcript files on disk. The Markdown formatting is entirely a storage-layer concern.

## Files

No files to modify.

## Verification

1. Verify the UI still works after the BE changes — fetch a channel with limit=1 and confirm progress and results display correctly
