import { useState, useCallback } from "react";
import type { VideoInfo, VideoProgressItem, FetchProgress, FetchStatus, SSEEvent, WhisperModel } from "../types";

interface UseFetchResult {
  videos: VideoInfo[];
  videoProgress: VideoProgressItem[];
  progress: FetchProgress;
  status: FetchStatus;
  error: string | null;
  withTranscript: number;
  withWhisper: number;
  startFetch: (url: string, lang: string, whisperModel?: WhisperModel | null, limit?: number | null) => void;
}

export function useFetchTranscripts(): UseFetchResult {
  const [videos, setVideos] = useState<VideoInfo[]>([]);
  const [progress, setProgress] = useState<FetchProgress>({ current: 0, total: 0 });
  const [status, setStatus] = useState<FetchStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const [withTranscript, setWithTranscript] = useState(0);
  const [withWhisper, setWithWhisper] = useState(0);
  const [videoProgress, setVideoProgress] = useState<VideoProgressItem[]>([]);

  const startFetch = useCallback(async (url: string, lang: string, whisperModel: WhisperModel | null = null, limit: number | null = null) => {
    setVideos([]);
    setProgress({ current: 0, total: 0 });
    setStatus("loading");
    setError(null);
    setWithTranscript(0);
    setWithWhisper(0);
    setVideoProgress([]);

    try {
      const response = await fetch("/api/fetch-transcripts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url,
          lang,
          whisper_model: whisperModel,
          ...(limit != null && { limit }),
        }),
      });

      if (!response.ok) {
        const body = await response.json();
        throw new Error(body.detail || `HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data: SSEEvent = JSON.parse(line.slice(6));

          if (data.event === "video_list") {
            setVideoProgress(
              data.videos.map((v) => ({
                video_id: v.video_id,
                title: v.title,
                duration: v.duration,
                upload_date: v.upload_date,
                url: v.url,
                step: "pending" as const,
              }))
            );
            setProgress({ current: 0, total: data.total });
          } else if (data.event === "video_status") {
            setVideoProgress((prev) =>
              prev.map((item) =>
                item.video_id === data.video_id
                  ? { ...item, step: data.step }
                  : item
              )
            );
          } else if (data.event === "progress") {
            setVideos((prev) => [
              ...prev,
              {
                video_id: data.video_id,
                title: data.title,
                url: data.url,
                duration: data.duration,
                upload_date: data.upload_date,
                has_transcript: data.has_transcript,
                transcript_source: data.transcript_source,
              },
            ]);
            setProgress({ current: data.current, total: data.total });
          } else if (data.event === "done") {
            setWithTranscript(data.with_transcript);
            setWithWhisper(data.with_whisper);
            setStatus("done");
          } else if (data.event === "error") {
            setError(data.detail);
            setStatus("error");
          }
        }
      }

      setStatus((prev) => (prev === "loading" ? "done" : prev));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("error");
    }
  }, []);

  return { videos, videoProgress, progress, status, error, withTranscript, withWhisper, startFetch };
}
