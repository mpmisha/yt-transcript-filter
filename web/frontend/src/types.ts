export type WhisperModel = "tiny" | "base" | "small" | "medium";

export interface VideoInfo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  upload_date: string | null;
  has_transcript: boolean;
  transcript_source: "youtube" | "whisper" | null;
}

export interface FetchProgress {
  current: number;
  total: number;
}

export type FetchStatus = "idle" | "loading" | "done" | "error";

export interface SSEProgressEvent {
  event: "progress";
  current: number;
  total: number;
  video_id: string;
  title: string;
  duration: number | null;
  upload_date: string | null;
  url: string;
  has_transcript: boolean;
  transcript_source: "youtube" | "whisper" | null;
}

export interface SSEDoneEvent {
  event: "done";
  total: number;
  with_transcript: number;
  with_whisper: number;
  output_dir: string;
}

export interface SSEErrorEvent {
  event: "error";
  detail: string;
}

export type VideoStep =
  | "pending"
  | "checking_captions"
  | "captions_found"
  | "no_captions"
  | "downloading_audio"
  | "transcribing"
  | "whisper_complete"
  | "whisper_failed"
  | "skipped";

export interface SSEVideoListEvent {
  event: "video_list";
  total: number;
  videos: Array<{
    video_id: string;
    title: string;
    duration: number | null;
    upload_date: string | null;
    url: string;
  }>;
}

export interface SSEVideoStatusEvent {
  event: "video_status";
  video_id: string;
  step: VideoStep;
}

export interface VideoProgressItem {
  video_id: string;
  title: string;
  duration: number | null;
  upload_date: string | null;
  url: string;
  step: VideoStep;
}

export type SSEEvent =
  | SSEVideoListEvent
  | SSEVideoStatusEvent
  | SSEProgressEvent
  | SSEDoneEvent
  | SSEErrorEvent;
