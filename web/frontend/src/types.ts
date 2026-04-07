export interface VideoInfo {
  video_id: string;
  title: string;
  url: string;
  duration: number | null;
  upload_date: string | null;
  has_transcript: boolean;
  transcript_source: "youtube" | "cached" | null;
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
  transcript_source: "youtube" | "cached" | null;
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
  | "skipped"
  | "cached";

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

export interface FilterResult {
  video_id: string;
  title: string;
  url: string;
  relevance_score: number;
  explanation: string;
  relevant: boolean;
}

export interface SSEFilterStartEvent {
  event: "filter_start";
  total: number;
  topic: string;
}

export interface SSEFilterProgressEvent {
  event: "filter_progress";
  current: number;
  total: number;
  video_id: string;
  title: string;
  url: string;
  relevance_score: number;
  explanation: string;
  relevant: boolean;
}

export interface SSEFilterDoneEvent {
  event: "filter_done";
  total: number;
  relevant_count: number;
  topic: string;
}

export interface SSEFilterErrorEvent {
  event: "filter_error";
  detail: string;
}

export type SSEFilterEvent =
  | SSEFilterStartEvent
  | SSEFilterProgressEvent
  | SSEFilterDoneEvent
  | SSEFilterErrorEvent;

export type FilterStatus = "idle" | "loading" | "done" | "error";
