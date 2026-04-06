import { useState } from "react";

interface FetchFormProps {
  onSubmit: (url: string, lang: string, limit: number | null) => void;
  disabled: boolean;
}

export function FetchForm({ onSubmit, disabled }: FetchFormProps) {
  const [url, setUrl] = useState("https://www.youtube.com/@starterstory");
  const [limit, setLimit] = useState<string>("1");

  const handleSubmit = () => {
    if (!url.trim()) return;
    const parsedLimit = limit.trim() ? parseInt(limit.trim(), 10) : null;
    const validLimit = parsedLimit !== null && parsedLimit >= 1 ? parsedLimit : null;
    onSubmit(url.trim(), "en", validLimit);
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
    </div>
  );
}
