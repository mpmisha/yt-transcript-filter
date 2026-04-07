# BE Developer — Default Transcript View on Load

## Goal

No changes needed for the backend layer.

## Rationale

The `load_index()` function in `src/storage.py` already reads `_index.json` and returns the list of video entries. The API layer will import and call it directly.

## Files

No files to modify.

## Verification

1. No changes to verify — existing functions remain unchanged
