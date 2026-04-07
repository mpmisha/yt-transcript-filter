import type { VideoProgressItem, VideoStep } from "../types";

interface VideoProgressListProps {
  items: VideoProgressItem[];
}

function getStepIcon(step: VideoStep): string {
  switch (step) {
    case "pending":
      return "⬜";
    case "checking_captions":
      return "⏳";
    case "captions_found":
      return "✅";
    case "no_captions":
      return "⚠️";
    case "skipped":
      return "⏭️";
    case "cached":
      return "📦";
  }
}

function getStepLabel(step: VideoStep): string {
  switch (step) {
    case "pending":
      return "Pending";
    case "checking_captions":
      return "Checking captions…";
    case "captions_found":
      return "YouTube captions";
    case "no_captions":
      return "No captions found";
    case "skipped":
      return "Skipped";
    case "cached":
      return "Cached locally";
  }
}

function getStepClass(step: VideoStep): string {
  switch (step) {
    case "pending":
      return "step-pending";
    case "checking_captions":
      return "step-active";
    case "captions_found":
      return "step-success";
    case "no_captions":
      return "step-warning";
    case "skipped":
      return "step-skipped";
    case "cached":
      return "step-success";
  }
}

export function VideoProgressList({ items }: VideoProgressListProps) {
  return (
    <div className="video-progress-list">
      {items.map((item) => (
        <div
          key={item.video_id}
          className={`video-progress-item ${getStepClass(item.step)}`}
        >
          <span className="video-progress-icon">{getStepIcon(item.step)}</span>
          <span className="video-progress-title">{item.title}</span>
          <span className="video-progress-step">{getStepLabel(item.step)}</span>
          {item.error && (
            <span className="video-progress-error">{item.error}</span>
          )}
        </div>
      ))}
    </div>
  );
}
