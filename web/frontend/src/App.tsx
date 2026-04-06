import { FetchForm } from "./components/FetchForm";
import { VideoTable } from "./components/VideoTable";
import { ProgressBar } from "./components/ProgressBar";
import { SummaryCard } from "./components/SummaryCard";
import { ErrorMessage } from "./components/ErrorMessage";
import { VideoProgressList } from "./components/VideoProgressList";
import { useFetchTranscripts } from "./hooks/useFetchTranscripts";
import "./App.css";

function App() {
  const { videos, videoProgress, progress, status, error, withTranscript, startFetch } =
    useFetchTranscripts();

  return (
    <div className="app">
      <h1>YouTube Transcript Fetcher</h1>
      <FetchForm onSubmit={startFetch} disabled={status === "loading"} />
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
      {videos.length > 0 && <VideoTable videos={videos} />}
    </div>
  );
}

export default App;
