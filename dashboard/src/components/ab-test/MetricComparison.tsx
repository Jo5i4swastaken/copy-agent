"use client";

import React from "react";

// ---------------------------------------------------------------------------
// MetricComparison — Side-by-side metric cards for control vs treatment
// ---------------------------------------------------------------------------

interface MetricComparisonProps {
  metricType: string;
  controlVariantId: string;
  treatmentVariantId: string;
  controlValue: number | null;
  treatmentValue: number | null;
  controlSampleSize?: number;
  treatmentSampleSize?: number;
}

function formatMetricLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatValue(value: number | null): string {
  if (value === null) return "--";
  if (value < 1) return (value * 100).toFixed(2) + "%";
  if (value >= 1000)
    return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
  return value.toFixed(2);
}

function computeLift(
  control: number | null,
  treatment: number | null,
): { pct: string; positive: boolean } | null {
  if (control === null || treatment === null || control === 0) return null;
  const lift = ((treatment - control) / control) * 100;
  return {
    pct: `${lift >= 0 ? "+" : ""}${lift.toFixed(1)}%`,
    positive: lift >= 0,
  };
}

/**
 * Displays a metric comparison between control and treatment variants
 * in a side-by-side card layout. Shows values, sample sizes, and
 * percentage lift.
 */
export function MetricComparison({
  metricType,
  controlVariantId,
  treatmentVariantId,
  controlValue,
  treatmentValue,
  controlSampleSize,
  treatmentSampleSize,
}: MetricComparisonProps) {
  const lift = computeLift(controlValue, treatmentValue);

  return (
    <div className="rounded-card border border-border-subtle bg-surface p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">
          {formatMetricLabel(metricType)}
        </h3>
        {lift && (
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-badge text-badge font-medium ${
              lift.positive
                ? "bg-success/10 text-success"
                : "bg-error/10 text-error"
            }`}
          >
            {lift.pct} lift
          </span>
        )}
      </div>

      {/* Side-by-side values */}
      <div className="grid grid-cols-2 gap-4">
        {/* Control */}
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted font-medium uppercase tracking-wide">
            Control
          </span>
          <span className="text-kpi-sm font-display text-foreground tabular-nums">
            {formatValue(controlValue)}
          </span>
          <span className="text-xs text-muted truncate" title={controlVariantId}>
            {controlVariantId}
          </span>
          {controlSampleSize !== undefined && (
            <span className="text-xs text-muted tabular-nums">
              n = {controlSampleSize.toLocaleString()}
            </span>
          )}
        </div>

        {/* Treatment */}
        <div className="flex flex-col gap-1">
          <span className="text-xs text-muted font-medium uppercase tracking-wide">
            Treatment
          </span>
          <span className="text-kpi-sm font-display text-foreground tabular-nums">
            {formatValue(treatmentValue)}
          </span>
          <span className="text-xs text-muted truncate" title={treatmentVariantId}>
            {treatmentVariantId}
          </span>
          {treatmentSampleSize !== undefined && (
            <span className="text-xs text-muted tabular-nums">
              n = {treatmentSampleSize.toLocaleString()}
            </span>
          )}
        </div>
      </div>

      {/* Visual bar comparison */}
      {controlValue !== null && treatmentValue !== null && (
        <div className="mt-4 flex flex-col gap-2">
          <BarComparison
            label="Control"
            value={controlValue}
            maxValue={Math.max(controlValue, treatmentValue)}
            color="bg-muted/40"
          />
          <BarComparison
            label="Treatment"
            value={treatmentValue}
            maxValue={Math.max(controlValue, treatmentValue)}
            color={
              treatmentValue >= controlValue
                ? "bg-success/60"
                : "bg-error/60"
            }
          />
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// BarComparison — Simple CSS bar for visual comparison
// ---------------------------------------------------------------------------

function BarComparison({
  label,
  value,
  maxValue,
  color,
}: {
  label: string;
  value: number;
  maxValue: number;
  color: string;
}) {
  const pct = maxValue > 0 ? (value / maxValue) * 100 : 0;

  return (
    <div className="flex items-center gap-3">
      <span className="text-xs text-muted w-16 flex-shrink-0">{label}</span>
      <div className="flex-1 h-2.5 rounded-full bg-elevated overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-slow ${color}`}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
    </div>
  );
}
