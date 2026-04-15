"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import { TestStateTimeline } from "@/components/ab-test/TestStateTimeline";
import { MetricComparison } from "@/components/ab-test/MetricComparison";
import { StatisticalResult } from "@/components/ab-test/StatisticalResult";

interface ABTestState {
  test_id: string;
  campaign_id: string;
  state: string;
  state_history: { state: string; entered_at: string; exited_at: string | null }[];
  hypothesis: string;
  variable_tested: string;
  variants: Record<string, { variant_id: string; description?: string; platform_id?: string | null }>;
  decision_criteria: {
    primary_metric: string;
    minimum_sample_size: number;
    minimum_confidence_level: number;
    maximum_duration_days: number;
  };
  current_metrics: Record<string, Record<string, number>>;
  checks_performed: { checked_at: string; verdict: string; p_value?: number }[];
  result?: { winner?: string; effect_size?: number; p_value?: number };
  winner?: string | null;
  next_check_at?: string;
}

export default function ABTestDetailPage() {
  const params = useParams();
  const testId = params.testId as string;
  const [test, setTest] = useState<ABTestState | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch("/api/ab-tests");
        if (!res.ok) throw new Error("Failed to fetch tests");
        const tests: ABTestState[] = await res.json();
        const found = tests.find((t) => t.test_id === decodeURIComponent(testId));
        if (!found) throw new Error(`Test '${testId}' not found`);
        setTest(found);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Unknown error");
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [testId]);

  if (isLoading) {
    return (
      <div className="animate-fade-in px-6 py-8 lg:px-10">
        <div className="skeleton mb-4 h-8 w-64 rounded" />
        <div className="skeleton mb-8 h-4 w-96 rounded" />
        <div className="skeleton h-20 w-full rounded-card" />
      </div>
    );
  }

  if (error || !test) {
    return (
      <div className="animate-fade-in px-6 py-8 lg:px-10">
        <div className="rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error" role="alert">
          {error || "Test not found"}
        </div>
      </div>
    );
  }

  // Build timestamps map for timeline
  const timestamps: Record<string, string> = {};
  for (const entry of test.state_history) {
    timestamps[entry.state] = entry.entered_at;
  }

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-foreground">
          {test.test_id}
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Campaign: {test.campaign_id} | Variable: {test.variable_tested}
        </p>
      </div>

      {/* State timeline */}
      <div className="mb-8 rounded-card border border-border bg-surface p-6 shadow-card">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-muted">
          Test Progress
        </h2>
        <TestStateTimeline
          currentState={test.state}
          createdAt={test.state_history[0]?.entered_at ?? ""}
          timestamps={timestamps}
        />
      </div>

      {/* Hypothesis */}
      <div className="mb-6 rounded-card border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-2 text-sm font-semibold uppercase tracking-wider text-muted">
          Hypothesis
        </h2>
        <p className="text-sm text-foreground">{test.hypothesis || "No hypothesis specified"}</p>
      </div>

      {/* Metric comparison */}
      {test.current_metrics && Object.keys(test.current_metrics).length > 0 && (
        <div className="mb-6">
          <MetricComparison
            metrics={test.current_metrics}
            primaryMetric={test.decision_criteria.primary_metric}
          />
        </div>
      )}

      {/* Statistical result */}
      {test.result && (
        <div className="mb-6">
          <StatisticalResult
            result={test.result}
            winner={test.winner}
            confidenceLevel={test.decision_criteria.minimum_confidence_level}
          />
        </div>
      )}

      {/* Decision criteria */}
      <div className="mb-6 rounded-card border border-border bg-surface p-5 shadow-card">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
          Decision Criteria
        </h2>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div>
            <p className="text-xs text-muted">Primary Metric</p>
            <p className="text-sm font-medium text-foreground">{test.decision_criteria.primary_metric}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Min Sample Size</p>
            <p className="text-sm font-medium text-foreground">{test.decision_criteria.minimum_sample_size}</p>
          </div>
          <div>
            <p className="text-xs text-muted">Confidence Level</p>
            <p className="text-sm font-medium text-foreground">{(test.decision_criteria.minimum_confidence_level * 100).toFixed(0)}%</p>
          </div>
          <div>
            <p className="text-xs text-muted">Max Duration</p>
            <p className="text-sm font-medium text-foreground">{test.decision_criteria.maximum_duration_days} days</p>
          </div>
        </div>
      </div>

      {/* Check history */}
      {test.checks_performed.length > 0 && (
        <div className="rounded-card border border-border bg-surface p-5 shadow-card">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
            Check History ({test.checks_performed.length})
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border-subtle text-left text-xs text-muted">
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 pr-4">Verdict</th>
                  <th className="pb-2">p-value</th>
                </tr>
              </thead>
              <tbody>
                {test.checks_performed.map((check, i) => (
                  <tr key={i} className="border-b border-border-subtle/50">
                    <td className="py-2 pr-4 text-foreground-secondary tabular-nums">
                      {new Date(check.checked_at).toLocaleString("en-US", {
                        month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                      })}
                    </td>
                    <td className="py-2 pr-4 font-medium text-foreground">{check.verdict}</td>
                    <td className="py-2 text-muted tabular-nums">
                      {check.p_value != null ? check.p_value.toFixed(4) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
