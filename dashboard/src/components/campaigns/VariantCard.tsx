"use client";

import type { Variant, MetricEntry } from "@/lib/types";
import { ChannelBadge } from "./ChannelBadge";
import { StatusBadge } from "./StatusBadge";

// ---------------------------------------------------------------------------
// VariantCard — displays a single copy variant on the campaign detail page
// ---------------------------------------------------------------------------

interface VariantCardProps {
  variant: Variant;
  isWinner?: boolean;
  metrics?: MetricEntry[];
}

export function VariantCard({ variant, isWinner, metrics }: VariantCardProps) {
  // Group metrics by type for the summary
  const metricSummary = metrics?.reduce<Record<string, number[]>>(
    (acc, entry) => {
      if (!acc[entry.metric_type]) acc[entry.metric_type] = [];
      acc[entry.metric_type].push(entry.value);
      return acc;
    },
    {},
  );

  return (
    <article
      className={`relative rounded-card border bg-surface p-5 shadow-card transition-colors duration-normal ${
        isWinner
          ? "border-warning/50 ring-1 ring-warning/20"
          : "border-border"
      }`}
      aria-label={`Variant ${variant.variant_id}${isWinner ? " - Winner" : ""}`}
    >
      {/* Winner badge */}
      {isWinner && (
        <div className="absolute -top-2.5 right-4">
          <span className="inline-flex items-center gap-1 rounded-badge bg-warning/15 px-2.5 py-0.5 text-badge font-semibold text-warning">
            <svg
              width="12"
              height="12"
              viewBox="0 0 12 12"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M6 1l1.545 3.13L11 4.635 8.5 7.07l.59 3.44L6 8.885 2.91 10.51l.59-3.44L1 4.635l3.455-.505L6 1z" />
            </svg>
            Winner
          </span>
        </div>
      )}

      {/* Header: variant ID + badges */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-foreground">
          {variant.variant_id}
        </span>
        <ChannelBadge channel={variant.channel} />
        <StatusBadge status={variant.status} />
        {variant.tone && (
          <span className="inline-flex items-center rounded-badge bg-accent/10 px-2 py-0.5 text-badge text-accent">
            {variant.tone}
          </span>
        )}
      </div>

      {/* Subject line (primarily for email) */}
      {variant.subject_line && (
        <div className="mb-3">
          <h4 className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">
            Subject Line
          </h4>
          <p className="text-sm font-medium text-foreground">
            {variant.subject_line}
          </p>
        </div>
      )}

      {/* Content body */}
      <div className="mb-3">
        <h4 className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">
          Content
        </h4>
        <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground-secondary">
          {variant.content}
        </p>
      </div>

      {/* CTA */}
      {variant.cta && (
        <div className="mb-3">
          <h4 className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">
            Call to Action
          </h4>
          <p className="text-sm font-medium text-accent">{variant.cta}</p>
        </div>
      )}

      {/* Notes */}
      {variant.notes && (
        <div className="mb-3">
          <h4 className="mb-1 text-xs font-medium uppercase tracking-wider text-muted">
            Notes
          </h4>
          <p className="text-sm italic text-muted">{variant.notes}</p>
        </div>
      )}

      {/* Metrics summary */}
      {metricSummary && Object.keys(metricSummary).length > 0 && (
        <div className="mt-4 border-t border-border-subtle pt-4">
          <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-muted">
            Metrics
          </h4>
          <div className="flex flex-wrap gap-3">
            {Object.entries(metricSummary).map(([type, values]) => {
              const avg = values.reduce((a, b) => a + b, 0) / values.length;
              return (
                <div
                  key={type}
                  className="flex flex-col items-center rounded-badge bg-elevated px-3 py-2"
                >
                  <span className="text-xs text-muted">
                    {formatMetricLabel(type)}
                  </span>
                  <span className="text-sm font-semibold text-foreground">
                    {formatMetricValue(avg)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </article>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMetricLabel(type: string): string {
  return type
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(value: number): string {
  if (value >= 1000) return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (value < 1) return (value * 100).toFixed(1) + "%";
  return value.toFixed(2);
}
