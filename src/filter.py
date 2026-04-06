"""Filter and search transcripts by keywords/topics."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .storage import load_index, load_transcript


@dataclass
class SearchResult:
    """A video that matched a search query."""
    video_id: str
    title: str
    url: str
    matches: int  # number of keyword occurrences
    snippets: list[str]  # text snippets around matches


def keyword_search(
    output_dir: str,
    keywords: list[str],
    case_sensitive: bool = False,
) -> list[SearchResult]:
    """
    Search all transcripts for the given keywords.
    Returns a list of matching videos sorted by relevance (match count).
    """
    index = load_index(output_dir)
    results = []

    flags = 0 if case_sensitive else re.IGNORECASE

    for entry in index:
        if not entry["has_transcript"]:
            continue

        text = load_transcript(output_dir, entry["file"])
        total_matches = 0
        snippets = []

        for keyword in keywords:
            matches = list(re.finditer(re.escape(keyword), text, flags))
            total_matches += len(matches)

            # Extract snippets around the first few matches
            for match in matches[:3]:
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                snippet = text[start:end].strip()
                snippets.append(f"...{snippet}...")

        if total_matches > 0:
            results.append(SearchResult(
                video_id=entry["video_id"],
                title=entry["title"],
                url=entry["url"],
                matches=total_matches,
                snippets=snippets[:5],  # limit snippets
            ))

    results.sort(key=lambda r: r.matches, reverse=True)
    return results


def filter_by_topic(
    output_dir: str,
    include_keywords: list[str] | None = None,
    exclude_keywords: list[str] | None = None,
) -> list[dict]:
    """
    Filter videos: include those matching include_keywords,
    exclude those matching exclude_keywords.
    Returns filtered metadata entries.
    """
    index = load_index(output_dir)
    filtered = []

    for entry in index:
        if not entry["has_transcript"]:
            continue

        text = load_transcript(output_dir, entry["file"]).lower()

        # Check exclusions first
        if exclude_keywords:
            if any(kw.lower() in text for kw in exclude_keywords):
                continue

        # Check inclusions
        if include_keywords:
            if not any(kw.lower() in text for kw in include_keywords):
                continue

        filtered.append(entry)

    return filtered
