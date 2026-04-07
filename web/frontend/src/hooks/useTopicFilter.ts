import { useCallback, useState } from "react";
import type { FilterResult, FilterStatus, SSEFilterEvent } from "../types";

interface TopicFilterProgress {
  current: number;
  total: number;
}

interface UseTopicFilterResult {
  results: FilterResult[];
  filterStatus: FilterStatus;
  filterError: string | null;
  filterProgress: TopicFilterProgress;
  relevantCount: number;
  startFilter: (topic: string, threshold: number) => Promise<void>;
  resetFilter: () => void;
}

export function useTopicFilter(): UseTopicFilterResult {
  const [results, setResults] = useState<FilterResult[]>([]);
  const [filterStatus, setFilterStatus] = useState<FilterStatus>("idle");
  const [filterError, setFilterError] = useState<string | null>(null);
  const [filterProgress, setFilterProgress] = useState<TopicFilterProgress>({
    current: 0,
    total: 0,
  });
  const [relevantCount, setRelevantCount] = useState(0);

  const resetFilter = useCallback(() => {
    setResults([]);
    setFilterStatus("idle");
    setFilterError(null);
    setFilterProgress({ current: 0, total: 0 });
    setRelevantCount(0);
  }, []);

  const startFilter = useCallback(async (topic: string, threshold: number) => {
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
            if (data.relevant) {
              setRelevantCount((prev) => prev + 1);
            }
          } else if (data.event === "filter_done") {
            setRelevantCount(data.relevant_count);
            setFilterProgress((prev) => ({ ...prev, total: data.total }));
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

  return {
    results,
    filterStatus,
    filterError,
    filterProgress,
    relevantCount,
    startFilter,
    resetFilter,
  };
}
