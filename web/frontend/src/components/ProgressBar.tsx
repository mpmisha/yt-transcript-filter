interface ProgressBarProps {
  current: number;
  total: number;
}

export function ProgressBar({ current, total }: ProgressBarProps) {
  if (total <= 0) return null;

  const percentage = Math.round((current / total) * 100);

  return (
    <div className="progress-bar">
      <progress value={current} max={total} />
      <span>
        {current} / {total} videos processed ({percentage}%)
      </span>
    </div>
  );
}
