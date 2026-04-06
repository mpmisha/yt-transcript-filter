import type { VideoProgressItem, VideoStep } from "../types";

interface VideoProgressListProps {
  items: VideoProgressItem[];
}

function getStepIcon(step: VideoStep): string {
  switch (step) {
    case "pending":
      return "⬜";
    case "checking_captions":
    case "downloading_audio":
    case "transcribing":
      return "⏳";
    case "captions_found":
      return "✅";
    case "no_captions":
      return "⚠️";
    case "whisper_complete":
      return "🎤";
    case "whisper_failed":
      return "❌";
    case "skipped":
      return "⏭️";
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
    case "downloading_audio":
      return "Downloading audio…";
    case "transcribing":
      return "Transcribing…";
    case "whisper_complete":
      return "Whisper (complete)";
    case "whisper_failed":
      return "Whisper (failed)";
    case "skipped":
      return "Skipped";
  }
}

function getStepClass(step: VideoStep): string {
  switch (step) {
    case "pending":
      return "step-pending";
    case "checking_captions":
    case "downloading_audio":
    case "transcribing":
      return "step-active";
    case "captions_found":
    case "whisper_complete":
      return "step-success";
    case "no_captions":
      return "step-warning";
    case "whisper_failed":
      return "step-error";
    case "skipped":
      return "step-skipped";
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
        </div>
      ))}
    </div>
  );
}
