"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";

interface Report {
  report_id: string;
  report_type: string;
  generated_at: string;
  parameters: Record<string, string>;
  content: Record<string, unknown>;
}

export default function ReportDetailPage() {
  const params = useParams();
  const reportId = params.reportId as string;
  const [report, setReport] = useState<Report | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/api/reports/${encodeURIComponent(reportId)}`);
        if (!res.ok) throw new Error("Failed to fetch report");
        const data = await res.json();
        setReport(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [reportId]);

  if (isLoading) {
    return (
      <div className="animate-fade-in px-6 py-8 lg:px-10">
        <div className="skeleton mb-4 h-8 w-64 rounded" />
        <div className="skeleton h-64 w-full rounded-card" />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="animate-fade-in px-6 py-8 lg:px-10">
        <div className="rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error" role="alert">
          {error || "Report not found"}
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-foreground">
          {report.report_type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          {report.report_id} | Generated{" "}
          {new Date(report.generated_at).toLocaleString("en-US", {
            month: "short", day: "numeric", year: "numeric",
            hour: "2-digit", minute: "2-digit",
          })}
        </p>
      </div>

      {/* Render content as formatted cards */}
      <div className="space-y-4">
        {Object.entries(report.content).map(([key, value]) => (
          <div key={key} className="rounded-card border border-border bg-surface p-5 shadow-card">
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
              {key.replace(/_/g, " ")}
            </h2>
            {typeof value === "object" && value !== null ? (
              <pre className="overflow-x-auto rounded bg-elevated p-3 text-xs text-foreground-secondary">
                {JSON.stringify(value, null, 2)}
              </pre>
            ) : (
              <p className="text-sm text-foreground">{String(value)}</p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
