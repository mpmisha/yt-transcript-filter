interface SummaryCardProps {
  total: number;
  withTranscript: number;
  withWhisper: number;
}

export function SummaryCard({ total, withTranscript, withWhisper }: SummaryCardProps) {
  return (
    <div className="summary-card">
      <p>✅ {withTranscript} / {total} videos have transcripts</p>
      {withWhisper > 0 && (
        <p>🎤 {withWhisper} transcribed by Whisper</p>
      )}
    </div>
  );
}
