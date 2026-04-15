"use client";

import { useReports } from "@/hooks/useReports";
import Link from "next/link";

const TYPE_COLORS: Record<string, string> = {
  campaign_performance: "bg-blue-500/10 text-blue-400",
  channel_trends: "bg-purple-500/10 text-purple-400",
  cross_channel_insights: "bg-accent/10 text-accent",
  playbook_health: "bg-success/10 text-success",
  anomaly_alerts: "bg-error/10 text-error",
};

const TYPE_LABELS: Record<string, string> = {
  campaign_performance: "Campaign Performance",
  channel_trends: "Channel Trends",
  cross_channel_insights: "Cross-Channel Insights",
  playbook_health: "Playbook Health",
  anomaly_alerts: "Anomaly Alerts",
};

function SkeletonCard() {
  return (
    <div className="rounded-card border border-border bg-surface p-5 shadow-card" aria-hidden="true">
      <div className="mb-3 flex items-center justify-between">
        <div className="skeleton h-5 w-32 rounded-badge" />
        <div className="skeleton h-4 w-20 rounded" />
      </div>
      <div className="skeleton h-4 w-2/3 rounded" />
    </div>
  );
}

export default function ReportsPage() {
  const { reports, isLoading, error } = useReports();

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-foreground">
          Reports
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Generated analytics reports and performance insights.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error" role="alert">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4" role="status">
          {Array.from({ length: 3 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!isLoading && !error && reports.length > 0 && (
        <div className="grid grid-cols-1 gap-4">
          {reports.map((report) => {
            const typeClass = TYPE_COLORS[report.report_type] ?? "bg-elevated text-muted";
            const typeLabel = TYPE_LABELS[report.report_type] ?? report.report_type;

            return (
              <Link
                key={report.report_id}
                href={`/reports/${encodeURIComponent(report.report_id)}`}
                className="block rounded-card border border-border bg-surface p-5 shadow-card transition-colors duration-fast hover:border-accent/40"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className={`rounded-badge px-2 py-0.5 text-xs font-medium ${typeClass}`}>
                      {typeLabel}
                    </span>
                    <span className="text-sm font-semibold text-foreground truncate">
                      {report.report_id}
                    </span>
                  </div>
                  <span className="text-xs text-muted tabular-nums">
                    {new Date(report.generated_at).toLocaleDateString("en-US", {
                      month: "short", day: "numeric", year: "numeric",
                    })}
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      {!isLoading && !error && reports.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-card border border-border-subtle bg-surface/50 px-6 py-16 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-elevated">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted" aria-hidden="true">
              <rect x="5" y="3" width="18" height="22" rx="2" />
              <path d="M10 8h8M10 12h8M10 16h5" strokeLinecap="round" />
            </svg>
          </div>
          <h2 className="mb-1 text-base font-semibold text-foreground">No reports yet</h2>
          <p className="max-w-sm text-sm text-muted">
            Use the chat panel to generate analytics reports for your campaigns.
          </p>
        </div>
      )}
    </div>
  );
}
