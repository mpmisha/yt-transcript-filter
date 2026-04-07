import { useMemo } from "react";
import type { FilterResult } from "../types";

interface FilterResultsListProps {
  results: FilterResult[];
  relevantCount: number;
  total: number;
}

function getScoreClass(score: number): "score-high" | "score-medium" | "score-low" {
  if (score >= 8) return "score-high";
  if (score >= 5) return "score-medium";
  return "score-low";
}

export function FilterResultsList({ results, relevantCount, total }: FilterResultsListProps) {
  const sortedResults = useMemo(
    () => [...results].sort((left, right) => right.relevance_score - left.relevance_score),
    [results]
  );

  return (
    <section className="filter-results">
      <div className="filter-results-summary">
        🎯 {relevantCount} / {total} videos matched your topic
      </div>
      <div className="filter-results-list">
        {sortedResults.map((result) => (
          <article
            key={result.video_id}
            className={`filter-result-item ${getScoreClass(result.relevance_score)}`}
          >
            <div className="filter-result-score">{result.relevance_score}</div>
            <div className="filter-result-content">
              <a href={result.url} target="_blank" rel="noopener noreferrer" className="filter-result-title">
                {result.title}
              </a>
              <p className="filter-result-explanation">{result.explanation}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
