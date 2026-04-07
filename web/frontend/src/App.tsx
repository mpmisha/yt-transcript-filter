import { useMemo, useState } from "react";
import { FetchForm } from "./components/FetchForm";
import { VideoTable } from "./components/VideoTable";
import { TranscriptModal } from "./components/TranscriptModal";
import { ProgressBar } from "./components/ProgressBar";
import { SummaryCard } from "./components/SummaryCard";
import { ErrorMessage } from "./components/ErrorMessage";
import { VideoProgressList } from "./components/VideoProgressList";
import { TopicFilterPanel } from "./components/TopicFilterPanel";
import { FilterResultsList } from "./components/FilterResultsList";
import { useFetchTranscripts } from "./hooks/useFetchTranscripts";
import { useTopicFilter } from "./hooks/useTopicFilter";
import "./App.css";

function App() {
  const { videos, videoProgress, progress, status, error, withTranscript, startFetch } =
    useFetchTranscripts();
  const {
    results: filterResults,
    filterStatus,
    filterError,
    filterProgress,
    relevantCount,
    startFilter,
    resetFilter,
  } = useTopicFilter();

  const [selectedVideo, setSelectedVideo] = useState<{
    videoId: string;
    title: string;
  } | null>(null);

  const hasTranscripts = useMemo(
    () => videos.some((video) => video.has_transcript),
    [videos]
  );

  const canShowTopicFilter = status === "done" && hasTranscripts;

  const handleViewTranscript = (videoId: string, title: string) => {
    setSelectedVideo({ videoId, title });
  };

  const handleFetchSubmit = (url: string, lang: string, limit: number | null) => {
    resetFilter();
    startFetch(url, lang, limit);
  };

  const handleCloseModal = () => {
    setSelectedVideo(null);
  };

  return (
    <div className="app">
      <h1>YouTube Transcript Fetcher</h1>
      <FetchForm onSubmit={handleFetchSubmit} disabled={status === "loading"} />
      <ErrorMessage message={error} />
      {(status === "loading" || status === "done") && (
        <>
          <ProgressBar current={progress.current} total={progress.total} />
          {videoProgress.length > 0 && (
            <VideoProgressList items={videoProgress} />
          )}
        </>
      )}
      {status === "done" && (
        <SummaryCard
          total={progress.total}
          withTranscript={withTranscript}
        />
      )}
      {videos.length > 0 && (
        <VideoTable videos={videos} onViewTranscript={handleViewTranscript} />
      )}
      {canShowTopicFilter && (
        <>
          <TopicFilterPanel
            onFilter={startFilter}
            disabled={filterStatus === "loading"}
          />
          {filterStatus === "loading" && (
            <ProgressBar current={filterProgress.current} total={filterProgress.total} />
          )}
          <ErrorMessage message={filterError} />
          {filterStatus === "done" && filterResults.length > 0 && (
            <FilterResultsList
              results={filterResults}
              relevantCount={relevantCount}
              total={filterProgress.total}
            />
          )}
        </>
      )}
      {selectedVideo && (
        <TranscriptModal
          videoId={selectedVideo.videoId}
          title={selectedVideo.title}
          onClose={handleCloseModal}
        />
      )}
    </div>
  );
}

export default App;
