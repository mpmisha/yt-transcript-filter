# FE Developer — Topic Filter UI

## Goal

Build a "Filter by Topic" panel that appears after transcripts are fetched, a results list showing relevance-scored videos, and a hook to manage the SSE stream from the filter API.

## Files

| Action | Path |
|--------|------|
| **Modify** | `web/frontend/src/types.ts` |
| **Create** | `web/frontend/src/components/TopicFilterPanel.tsx` |
| **Create** | `web/frontend/src/components/FilterResultsList.tsx` |
| **Create** | `web/frontend/src/hooks/useTopicFilter.ts` |
| **Modify** | `web/frontend/src/App.tsx` |
| **Modify** | `web/frontend/src/App.css` |

## Blocked By

Nothing — all UI and type work is independent. Can start in parallel with BE Developer.

## Delivers

A complete topic filter UI: input panel, SSE-powered progress, and a ranked results list with relevance scores and AI explanations.

---

## Detailed Steps

### 1. Modify `types.ts` — Add filter types

Add these types at the end of the file:

```typescript
// --- Topic Filter Types ---

export interface FilterResult {
  video_id: string;
  title: string;
  url: string;
  relevance_score: number;
  explanation: string;
  relevant: boolean;
}

export interface SSEFilterStartEvent {
  event: "filter_start";
  total: number;
  topic: string;
}

export interface SSEFilterProgressEvent {
  event: "filter_progress";
  current: number;
  total: number;
  video_id: string;
  title: string;
  url: string;
  relevance_score: number;
  explanation: string;
  relevant: boolean;
}

export interface SSEFilterDoneEvent {
  event: "filter_done";
  total: number;
  relevant_count: number;
  topic: string;
}

export interface SSEFilterErrorEvent {
  event: "filter_error";
  detail: string;
}

export type SSEFilterEvent =
  | SSEFilterStartEvent
  | SSEFilterProgressEvent
  | SSEFilterDoneEvent
  | SSEFilterErrorEvent;

export type FilterStatus = "idle" | "loading" | "done" | "error";
```

---

### 2. Create `useTopicFilter.ts` hook

```typescript
import { useState, useCallback } from "react";
import type { FilterResult, FilterStatus, SSEFilterEvent } from "../types";

interface UseTopicFilterResult {
  results: FilterResult[];
  filterStatus: FilterStatus;
  filterError: string | null;
  filterProgress: { current: number; total: number };
  relevantCount: number;
  startFilter: (topic: string, threshold?: number) => void;
  resetFilter: () => void;
}

export function useTopicFilter(): UseTopicFilterResult {
  const [results, setResults] = useState<FilterResult[]>([]);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("idle");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [filterProgress, setFilterProgress] = useState({ current: 0, total: 0 });
  const [relevantCount, setRelevantCount] = useState(0);

  const resetFilter = useCallback(() => {
    setResults([]);
    setFilterStatus("idle");
    setFilterError(null);
    setFilterProgress({ current: 0, total: 0 });
    setRelevantCount(0);
  }, []);

  const startFilter = useCallback(async (topic: string, threshold: number = 5) => {
    setResults([]);
    setFilterStatus("loading");
    setFilterError(null);
    setFilterProgress({ current: 0, total: 0 });
    setRelevantCount(0);

    try {
      const response = await fetch("/api/filter-by-topic", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic, threshold }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data: SSEFilterEvent = JSON.parse(line.slice(6));

          if (data.event === "filter_start") {
            setFilterProgress({ current: 0, total: data.total });
          } else if (data.event === "filter_progress") {
            setResults((prev) => [
              ...prev,
              {
                video_id: data.video_id,
                title: data.title,
                url: data.url,
                relevance_score: data.relevance_score,
                explanation: data.explanation,
                relevant: data.relevant,
              },
            ]);
            setFilterProgress({ current: data.current, total: data.total });
          } else if (data.event === "filter_done") {
            setRelevantCount(data.relevant_count);
            setFilterStatus("done");
          } else if (data.event === "filter_error") {
            setFilterError(data.detail);
            setFilterStatus("error");
          }
        }
      }

      setFilterStatus((prev) => (prev === "loading" ? "done" : prev));
    } catch (err) {
      setFilterError(err instanceof Error ? err.message : "Unknown error");
      setFilterStatus("error");
    }
  }, []);

  return { results, filterStatus, filterError, filterProgress, relevantCount, startFilter, resetFilter };
}
```

This follows the exact same SSE parsing pattern as the existing `useFetchTranscripts` hook.

---

### 3. Create `TopicFilterPanel.tsx`

A simple panel with a text input for the topic and a "Filter" button:

```typescript
import { useState } from "react";

interface TopicFilterPanelProps {
  onFilter: (topic: string) => void;
  disabled: boolean;
}

export const TopicFilterPanel = ({ onFilter, disabled }: TopicFilterPanelProps) => {
  const [topic, setTopic] = useState("");

  const handleSubmit = () => {
    if (!topic.trim()) return;
    onFilter(topic.trim());
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit();
  };

  return (
    <div className="topic-filter-panel">
      <h3>🔍 Filter by Topic</h3>
      <p className="topic-filter-hint">
        Describe a topic and AI will score each video for relevance.
      </p>
      <div className="topic-filter-form">
        <input
          type="text"
          className="topic-input"
          placeholder='e.g. "bootstrapping a SaaS to $10k MRR"'
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button onClick={handleSubmit} disabled={disabled || !topic.trim()}>
          Filter
        </button>
      </div>
    </div>
  );
};
```

---

### 4. Create `FilterResultsList.tsx`

Displays scored results as a ranked list, sorted by relevance score descending:

```typescript
import type { FilterResult } from "../types";

interface FilterResultsListProps {
  results: FilterResult[];
  relevantCount: number;
  total: number;
}

const getScoreColor = (score: number): string => {
  if (score >= 8) return "#16a34a";
  if (score >= 5) return "#ca8a04";
  if (score >= 0) return "#dc2626";
  return "#6b7280";  // error state (score = -1)
};

const getScoreBadgeClass = (score: number): string => {
  if (score >= 8) return "score-high";
  if (score >= 5) return "score-medium";
  return "score-low";
};

export const FilterResultsList = ({ results, relevantCount, total }: FilterResultsListProps) => {
  const sorted = [...results].sort((a, b) => b.relevance_score - a.relevance_score);

  return (
    <div className="filter-results">
      <div className="filter-results-summary">
        <p>🎯 {relevantCount} / {total} videos are relevant to your topic</p>
      </div>
      <div className="filter-results-list">
        {sorted.map((result) => (
          <div key={result.video_id} className={`filter-result-item ${getScoreBadgeClass(result.relevance_score)}`}>
            <div className="filter-result-score" style={{ color: getScoreColor(result.relevance_score) }}>
              {result.relevance_score >= 0 ? result.relevance_score : "?"}
            </div>
            <div className="filter-result-content">
              <a href={result.url} target="_blank" rel="noopener noreferrer" className="filter-result-title">
                {result.title}
              </a>
              <p className="filter-result-explanation">{result.explanation}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
```

---

### 5. Modify `App.tsx` — Wire in the filter

#### 5a. Add imports

```typescript
import { TopicFilterPanel } from "./components/TopicFilterPanel";
import { FilterResultsList } from "./components/FilterResultsList";
import { useTopicFilter } from "./hooks/useTopicFilter";
```

#### 5b. Add the hook

Inside the `App` component, after the existing `useFetchTranscripts` hook:

```typescript
const { results: filterResults, filterStatus, filterError, filterProgress, relevantCount, startFilter, resetFilter } =
    useTopicFilter();
```

#### 5c. Add filter UI in the JSX

After the `{videos.length > 0 && <VideoTable ... />}` block, add:

```tsx
{status === "done" && videos.some((v) => v.has_transcript) && (
  <>
    <TopicFilterPanel
      onFilter={startFilter}
      disabled={filterStatus === "loading"}
    />
    {filterStatus === "loading" && (
      <ProgressBar current={filterProgress.current} total={filterProgress.total} />
    )}
    {filterError && <ErrorMessage message={filterError} />}
    {filterStatus === "done" && filterResults.length > 0 && (
      <FilterResultsList
        results={filterResults}
        relevantCount={relevantCount}
        total={filterProgress.total}
      />
    )}
  </>
)}
```

The filter panel only appears when:
- Fetching is complete (`status === "done"`)
- At least one video has a transcript

The existing `ProgressBar` and `ErrorMessage` components are reused for the filter progress.

---

### 6. Modify `App.css` — Add filter styles

Add at the end of the file:

```css
/* Topic Filter Panel */
.topic-filter-panel {
  background: #f0f4ff;
  border: 1px solid #c7d2fe;
  border-radius: 8px;
  padding: 1.2rem;
  margin: 1.5rem 0;
}

.topic-filter-panel h3 {
  margin: 0 0 0.3rem 0;
  font-size: 1.1rem;
  color: #1a1a2e;
}

.topic-filter-hint {
  margin: 0 0 0.8rem 0;
  font-size: 0.85rem;
  color: #6b7280;
}

.topic-filter-form {
  display: flex;
  gap: 0.5rem;
}

.topic-filter-form .topic-input {
  flex: 1;
  padding: 0.6rem 0.8rem;
  border: 1px solid #c7d2fe;
  border-radius: 6px;
  font-size: 0.95rem;
}

.topic-filter-form button {
  padding: 0.6rem 1.4rem;
  background: #6366f1;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 0.95rem;
  cursor: pointer;
  transition: background 0.2s;
}

.topic-filter-form button:hover:not(:disabled) {
  background: #4f46e5;
}

.topic-filter-form button:disabled {
  background: #a0a0a0;
  cursor: not-allowed;
}

/* Filter Results */
.filter-results {
  margin: 1.5rem 0;
}

.filter-results-summary {
  background: #ede9fe;
  border: 1px solid #c4b5fd;
  color: #4c1d95;
  padding: 0.8rem 1.2rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 1rem;
  font-weight: 500;
}

.filter-results-summary p {
  margin: 0;
}

.filter-results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-result-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  background: #fafafa;
  transition: background 0.2s;
}

.filter-result-item:hover {
  background: #f3f4f6;
}

.filter-result-item.score-high {
  border-left: 4px solid #16a34a;
}

.filter-result-item.score-medium {
  border-left: 4px solid #ca8a04;
}

.filter-result-item.score-low {
  border-left: 4px solid #dc2626;
}

.filter-result-score {
  font-size: 1.5rem;
  font-weight: 700;
  min-width: 36px;
  text-align: center;
  line-height: 1;
  padding-top: 2px;
}

.filter-result-content {
  flex: 1;
  min-width: 0;
}

.filter-result-title {
  color: #4361ee;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.95rem;
}

.filter-result-title:hover {
  text-decoration: underline;
}

.filter-result-explanation {
  margin: 4px 0 0 0;
  font-size: 0.85rem;
  color: #6b7280;
  line-height: 1.4;
}
```

---

## Verification

1. `cd web/frontend && npx tsc --noEmit` — no TypeScript errors
2. `cd web/frontend && npm run build` — builds successfully
3. `grep -ri "filter" web/frontend/src/types.ts` — filter types are present
4. Start dev servers, fetch a channel, see the "Filter by Topic" panel appear below the video table
5. Enter a topic, click Filter — progress bar shows, results appear ranked with scores
6. Scores ≥ 8 have green left border, 5-7 yellow, < 5 red
