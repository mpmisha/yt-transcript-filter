import { useState, useEffect, useCallback } from "react";

interface TranscriptModalProps {
  videoId: string;
  title: string;
  onClose: () => void;
}

export function TranscriptModal({ videoId, title, onClose }: TranscriptModalProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTranscript = async () => {
      try {
        const response = await fetch(`/api/transcripts/${videoId}`);
        if (!response.ok) {
          throw new Error("Failed to load transcript");
        }
        const data = await response.json();
        setContent(data.content);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setLoading(false);
      }
    };
    fetchTranscript();
  }, [videoId]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const handleOverlayClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="transcript-modal-overlay" onClick={handleOverlayClick}>
      <div className="transcript-modal">
        <div className="transcript-modal-header">
          <h2>{title}</h2>
          <button className="transcript-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>
        <div className="transcript-modal-body">
          {loading && <p>Loading transcript…</p>}
          {error && <p className="transcript-modal-error">Error: {error}</p>}
          {content && <pre className="transcript-content">{content}</pre>}
        </div>
      </div>
    </div>
  );
}
