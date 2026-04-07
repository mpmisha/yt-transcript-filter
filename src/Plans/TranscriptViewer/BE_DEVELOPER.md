# BE Developer — Transcript Viewer

## Goal

No changes needed for the backend layer.

## Rationale

The storage functions `load_index()` and `load_transcript()` already exist in `src/storage.py` and provide everything needed. The API layer will import and call them directly.

## Files

No files to modify.

## Reference

Existing functions in `src/storage.py` used by the API:

```python
def load_index(output_dir: str | Path) -> list[dict]:
    """Load the metadata index from a previously saved transcript directory."""

def load_transcript(output_dir: str | Path, filename: str) -> str:
    """Load a single transcript file."""
```

## Verification

1. No changes to verify — existing functions remain unchanged
