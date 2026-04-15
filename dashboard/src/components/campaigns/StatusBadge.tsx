"use client";

// ---------------------------------------------------------------------------
// Status color mapping
// ---------------------------------------------------------------------------

const STATUS_STYLES: Record<string, string> = {
  active: "bg-success-muted text-success",
  draft: "bg-warning-muted text-warning",
  complete: "bg-info-muted text-info",
  completed: "bg-info-muted text-info",
  paused: "bg-elevated text-muted",
};

const STATUS_LABELS: Record<string, string> = {
  active: "Active",
  draft: "Draft",
  complete: "Completed",
  completed: "Completed",
  paused: "Paused",
};

// ---------------------------------------------------------------------------
// StatusBadge
// ---------------------------------------------------------------------------

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();
  const styles = STATUS_STYLES[normalized] ?? "bg-elevated text-muted";
  const label = STATUS_LABELS[normalized] ?? status;

  return (
    <span
      className={`inline-flex items-center rounded-badge px-2 py-0.5 text-badge font-medium capitalize ${styles}`}
    >
      {label}
    </span>
  );
}
