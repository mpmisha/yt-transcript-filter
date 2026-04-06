export interface VideoInfo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  upload_date: string | null;
  has_transcript: boolean;
  transcript_source: "youtube" | null;
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
  transcript_source: "youtube" | null;
}

export interface SSEDoneEvent {
  event: "done";
  total: number;
  with_transcript: number;
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
  error?: string;
}

export interface VideoProgressItem {
  video_id: string;
  title: string;
  duration: number | null;
  upload_date: string | null;
  url: string;
  step: VideoStep;
  error?: string;
}

export type SSEEvent =
  | SSEVideoListEvent
  | SSEVideoStatusEvent
  | SSEProgressEvent
  | SSEDoneEvent
  | SSEErrorEvent;
