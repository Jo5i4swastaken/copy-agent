"use client";

interface Transfer {
  transfer_id: string;
  source_channel: string;
  target_channel: string;
  hypothesis: string;
  status: string;
  learning_text?: string;
  created_at?: string;
  result?: string;
}

interface TransferCardProps {
  transfer: Transfer;
}

const STATUS_COLORS: Record<string, string> = {
  proposed: "bg-yellow-500/10 text-yellow-400",
  testing: "bg-blue-500/10 text-blue-400",
  confirmed: "bg-success/10 text-success",
  rejected: "bg-error/10 text-error",
  inconclusive: "bg-foreground-secondary/10 text-foreground-secondary",
};

export function TransferCard({ transfer }: TransferCardProps) {
  const statusClass = STATUS_COLORS[transfer.status] ?? STATUS_COLORS.inconclusive;

  return (
    <div className="rounded-card border border-border bg-surface p-4 shadow-card">
      <div className="mb-2 flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
          <span className="rounded-badge bg-elevated px-2 py-0.5 text-xs">
            {transfer.source_channel}
          </span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
            <path d="M2 7h10M9 4l3 3-3 3" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="rounded-badge bg-elevated px-2 py-0.5 text-xs">
            {transfer.target_channel}
          </span>
        </div>
        <span className={`rounded-badge px-2 py-0.5 text-xs font-medium ${statusClass}`}>
          {transfer.status}
        </span>
      </div>

      <p className="mb-2 text-sm text-foreground-secondary line-clamp-2">
        {transfer.hypothesis}
      </p>

      {transfer.learning_text && (
        <p className="text-xs text-muted line-clamp-1">
          Source: {transfer.learning_text}
        </p>
      )}

      {transfer.created_at && (
        <p className="mt-2 text-xs text-muted tabular-nums">
          {new Date(transfer.created_at).toLocaleDateString("en-US", {
            month: "short",
            day: "numeric",
            year: "numeric",
          })}
        </p>
      )}
    </div>
  );
}
