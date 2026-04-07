import { useState } from "react";
import type { KeyboardEvent } from "react";

interface TopicFilterPanelProps {
  onFilter: (topic: string, threshold: number) => void | Promise<void>;
  disabled: boolean;
}

export function TopicFilterPanel({ onFilter, disabled }: TopicFilterPanelProps) {
  const [topic, setTopic] = useState("how to get your first 100 customers");
  const [threshold, setThreshold] = useState(5);

  const handleSubmit = () => {
    const trimmedTopic = topic.trim();
    if (!trimmedTopic) return;
    onFilter(trimmedTopic, threshold);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") {
      handleSubmit();
    }
  };

  return (
    <section className="topic-filter-panel">
      <h2>🔍 Filter by Topic</h2>
      <p className="topic-filter-hint">
        Describe what you care about and rank videos by relevance.
      </p>
      <div className="topic-filter-form">
        <input
          type="text"
          className="topic-input"
          placeholder='e.g. "bootstrapping a SaaS to $10k MRR"'
          value={topic}
          onChange={(event) => setTopic(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
        />
        <button onClick={handleSubmit} disabled={disabled || !topic.trim()}>
          Filter
        </button>
      </div>
      <div className="topic-threshold-row">
        <label htmlFor="topic-threshold">Relevance threshold: {threshold}</label>
        <input
          id="topic-threshold"
          type="range"
          min={0}
          max={10}
          value={threshold}
          onChange={(event) => setThreshold(Number(event.target.value))}
          disabled={disabled}
        />
      </div>
    </section>
  );
}
