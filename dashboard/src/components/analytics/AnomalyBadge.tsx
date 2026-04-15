"use client";

interface AnomalyBadgeProps {
  direction: "spike" | "drop";
  zScore: number;
  metric?: string;
}

export function AnomalyBadge({ direction, zScore, metric }: AnomalyBadgeProps) {
  const isSpike = direction === "spike";

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-badge px-2 py-0.5 text-xs font-medium ${
        isSpike
          ? "bg-error/10 text-error"
          : "bg-blue-500/10 text-blue-400"
      }`}
    >
      <svg
        width="12"
        height="12"
        viewBox="0 0 12 12"
        fill="none"
        aria-hidden="true"
      >
        <path
          d={isSpike ? "M6 2L10 8H2L6 2Z" : "M6 10L2 4H10L6 10Z"}
          fill="currentColor"
        />
      </svg>
      {metric ? `${metric}: ` : ""}
      {direction} (z={Math.abs(zScore).toFixed(1)})
    </span>
  );
}
