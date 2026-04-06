interface SummaryCardProps {
  total: number;
  withTranscript: number;
}

export function SummaryCard({ total, withTranscript }: SummaryCardProps) {
  return (
    <div className="summary-card">
      <p>✅ {withTranscript} / {total} videos have transcripts</p>
    </div>
  );
}
