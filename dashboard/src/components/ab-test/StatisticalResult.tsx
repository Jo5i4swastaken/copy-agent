"use client";

import React from "react";

// ---------------------------------------------------------------------------
// StatisticalResult — P-value, confidence interval, effect size display
// ---------------------------------------------------------------------------

interface StatisticalResultProps {
  pValue: number | null;
  effectSize: number | null;
  confidenceInterval: [number, number] | null;
  verdict: string;
  winner: string | null;
  reason?: string;
}

function getPValueColor(p: number | null): string {
  if (p === null) return "text-muted";
  if (p <= 0.01) return "text-success";
  if (p <= 0.05) return "text-success";
  if (p <= 0.1) return "text-warning";
  return "text-error";
}

function getPValueBgColor(p: number | null): string {
  if (p === null) return "bg-elevated";
  if (p <= 0.05) return "bg-success/10";
  if (p <= 0.1) return "bg-warning/10";
  return "bg-error/10";
}

function getEffectSizeLabel(effect: number | null): string {
  if (effect === null) return "N/A";
  const abs = Math.abs(effect);
  if (abs < 0.2) return "Negligible";
  if (abs < 0.5) return "Small";
  if (abs < 0.8) return "Medium";
  return "Large";
}

function getVerdictColor(verdict: string): string {
  const v = verdict.toLowerCase();
  if (v.includes("winner") || v.includes("significant") || v === "treatment_wins" || v === "control_wins") {
    return "text-success";
  }
  if (v.includes("inconclusive") || v.includes("continue") || v === "no_winner") {
    return "text-warning";
  }
  if (v.includes("insufficient") || v.includes("early")) {
    return "text-muted";
  }
  return "text-foreground";
}

function getVerdictBadge(verdict: string): { label: string; colorClass: string } {
  const v = verdict.toLowerCase();
  if (v.includes("treatment_wins") || v.includes("treatment wins")) {
    return { label: "Treatment Wins", colorClass: "bg-success/10 text-success" };
  }
  if (v.includes("control_wins") || v.includes("control wins")) {
    return { label: "Control Wins", colorClass: "bg-info/10 text-info" };
  }
  if (v.includes("no_winner") || v.includes("no winner") || v.includes("inconclusive")) {
    return { label: "Inconclusive", colorClass: "bg-warning/10 text-warning" };
  }
  if (v.includes("continue") || v.includes("collecting")) {
    return { label: "Collecting Data", colorClass: "bg-accent/10 text-accent" };
  }
  if (v.includes("insufficient")) {
    return { label: "Insufficient Data", colorClass: "bg-elevated text-muted" };
  }
  return { label: verdict, colorClass: "bg-elevated text-foreground-secondary" };
}

/**
 * Displays statistical analysis results for an A/B test with color-coded
 * significance indicators. Shows p-value, effect size, confidence interval,
 * and the verdict.
 */
export function StatisticalResult({
  pValue,
  effectSize,
  confidenceInterval,
  verdict,
  winner,
  reason,
}: StatisticalResultProps) {
  const verdictBadge = getVerdictBadge(verdict);

  return (
    <div className="rounded-card border border-border-subtle bg-surface p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-foreground">
          Statistical Result
        </h3>
        <span
          className={`inline-flex items-center px-2.5 py-1 rounded-badge text-badge font-medium ${verdictBadge.colorClass}`}
        >
          {verdictBadge.label}
        </span>
      </div>

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        {/* P-value */}
        <div
          className={`rounded-lg p-3 ${getPValueBgColor(pValue)}`}
        >
          <span className="text-xs text-muted font-medium uppercase tracking-wide block mb-1">
            P-Value
          </span>
          <span
            className={`text-lg font-display font-semibold tabular-nums ${getPValueColor(pValue)}`}
          >
            {pValue !== null ? pValue.toFixed(4) : "--"}
          </span>
          {pValue !== null && (
            <span className="text-xs text-muted block mt-0.5">
              {pValue <= 0.05
                ? "Statistically significant"
                : pValue <= 0.1
                  ? "Marginally significant"
                  : "Not significant"}
            </span>
          )}
        </div>

        {/* Effect size */}
        <div className="rounded-lg bg-elevated/50 p-3">
          <span className="text-xs text-muted font-medium uppercase tracking-wide block mb-1">
            Effect Size
          </span>
          <span className="text-lg font-display font-semibold text-foreground tabular-nums">
            {effectSize !== null ? effectSize.toFixed(3) : "--"}
          </span>
          <span className="text-xs text-muted block mt-0.5">
            {getEffectSizeLabel(effectSize)}
          </span>
        </div>

        {/* Confidence interval */}
        <div className="rounded-lg bg-elevated/50 p-3">
          <span className="text-xs text-muted font-medium uppercase tracking-wide block mb-1">
            95% CI
          </span>
          <span className="text-lg font-display font-semibold text-foreground tabular-nums">
            {confidenceInterval
              ? `[${confidenceInterval[0].toFixed(3)}, ${confidenceInterval[1].toFixed(3)}]`
              : "--"}
          </span>
          {confidenceInterval && (
            <span className="text-xs text-muted block mt-0.5">
              {confidenceInterval[0] > 0
                ? "Entire CI above zero"
                : confidenceInterval[1] < 0
                  ? "Entire CI below zero"
                  : "CI includes zero"}
            </span>
          )}
        </div>
      </div>

      {/* Winner and reason */}
      {(winner || reason) && (
        <div className="border-t border-border-subtle pt-3 mt-3">
          {winner && (
            <p className="text-sm text-foreground">
              <span className="font-medium">Winner: </span>
              <span className="font-mono text-accent">{winner}</span>
            </p>
          )}
          {reason && (
            <p className="text-sm text-foreground-secondary mt-1">
              {reason}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
