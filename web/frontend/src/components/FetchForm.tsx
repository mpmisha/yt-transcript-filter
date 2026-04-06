import { useState } from "react";
import type { WhisperModel } from "../types";

interface FetchFormProps {
  onSubmit: (url: string, lang: string, whisperModel: WhisperModel | null, limit: number | null) => void;
  disabled: boolean;
}

export function FetchForm({ onSubmit, disabled }: FetchFormProps) {
  const [url, setUrl] = useState("");
  const [whisperEnabled, setWhisperEnabled] = useState(false);
  const [whisperModel, setWhisperModel] = useState<WhisperModel>("base");
  const [limit, setLimit] = useState<string>("5");

  const handleSubmit = () => {
    if (!url.trim()) return;
    const parsedLimit = limit.trim() ? parseInt(limit.trim(), 10) : null;
    const validLimit = parsedLimit !== null && parsedLimit >= 1 ? parsedLimit : null;
    onSubmit(url.trim(), "en", whisperEnabled ? whisperModel : null, validLimit);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit();
  };

  return (
    <div className="fetch-form">
      <input
        type="text"
        className="url-input"
        placeholder="https://www.youtube.com/@ChannelName/videos"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <input
        type="number"
        className="limit-input"
        placeholder="All"
        min={1}
        value={limit}
        onChange={(e) => setLimit(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
      />
      <button onClick={handleSubmit} disabled={disabled || !url.trim()}>
        Fetch
      </button>
      <div className="whisper-toggle">
        <label>
          <input
            type="checkbox"
            checked={whisperEnabled}
            onChange={(e) => setWhisperEnabled(e.target.checked)}
            disabled={disabled}
          />
          Auto-transcribe with Whisper
        </label>
        {whisperEnabled && (
          <div className="whisper-model-select">
            <select
              value={whisperModel}
              onChange={(e) => setWhisperModel(e.target.value as WhisperModel)}
              disabled={disabled}
            >
              <option value="tiny">Tiny (fastest, basic quality)</option>
              <option value="base">Base (balanced)</option>
              <option value="small">Small (good quality, slower)</option>
              <option value="medium">Medium (best quality, slowest)</option>
            </select>
            <p className="whisper-info">First run downloads the model (~140MB for Base)</p>
          </div>
        )}
      </div>
    </div>
  );
}
