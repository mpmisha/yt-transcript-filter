import type { VideoInfo } from "../types";

interface VideoTableProps {
  videos: VideoInfo[];
  onViewTranscript: (videoId: string, title: string) => void;
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatTranscriptSource(source: string | null, hasTranscript: boolean): string {
  if (!hasTranscript) return "❌ None";
  if (source === "youtube") return "✅ YouTube";
  if (source === "cached") return "📦 Cached";
  return "✅";
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  if (dateStr.length === 8) {
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`;
  }
  return dateStr;
}

export function VideoTable({ videos, onViewTranscript }: VideoTableProps) {
  return (
    <div className="video-table-wrapper">
      <table className="video-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Title</th>
            <th>Duration</th>
            <th>Upload Date</th>
            <th>Transcript Source</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {videos.map((video, index) => (
            <tr key={video.video_id}>
              <td>{index + 1}</td>
              <td>
                <a href={video.url} target="_blank" rel="noopener noreferrer">
                  {video.title}
                </a>
              </td>
              <td>{formatDuration(video.duration)}</td>
              <td>{formatDate(video.upload_date)}</td>
              <td>{formatTranscriptSource(video.transcript_source, video.has_transcript)}</td>
              <td>
                {video.has_transcript && (
                  <button
                    className="view-transcript-btn"
                    onClick={() => onViewTranscript(video.video_id, video.title)}
                  >
                    View
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
