"use client";

// ---------------------------------------------------------------------------
// ConfidenceBar — Horizontal bar visualizing a 0-1 confidence score
//
// Color thresholds:
//   < 0.4  = confidence-low   (warm orange)
//   0.4-0.7 = confidence-medium (amber)
//   > 0.7  = confidence-high  (green)
// ---------------------------------------------------------------------------

interface ConfidenceBarProps {
  /** Confidence value between 0 and 1. */
  confidence: number;
}

function getConfidenceColor(confidence: number): string {
  if (confidence < 0.4) return "bg-confidence-low";
  if (confidence <= 0.7) return "bg-confidence-medium";
  return "bg-confidence-high";
}

function getConfidenceTextColor(confidence: number): string {
  if (confidence < 0.4) return "text-confidence-low";
  if (confidence <= 0.7) return "text-confidence-medium";
  return "text-confidence-high";
}

export function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const clamped = Math.max(0, Math.min(1, confidence));
  const pct = Math.round(clamped * 100);
  const barColor = getConfidenceColor(clamped);
  const textColor = getConfidenceTextColor(clamped);

  return (
    <div className="flex items-center gap-2">
      <div
        className="flex-1 h-2 rounded-full bg-elevated overflow-hidden"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Confidence: ${pct}%`}
      >
        <div
          className={`h-full rounded-full transition-all duration-normal ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className={`text-xs font-medium tabular-nums min-w-[2.5rem] text-right ${textColor}`}>
        {pct}%
      </span>
    </div>
  );
}
