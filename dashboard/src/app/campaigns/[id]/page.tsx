"use client";

import { useMemo } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useCampaign } from "@/hooks/useCampaigns";
import type { MetricEntry, MetricType, Variant } from "@/lib/types";
import { ChannelBadge } from "@/components/campaigns/ChannelBadge";
import { StatusBadge } from "@/components/campaigns/StatusBadge";
import { VariantCard } from "@/components/campaigns/VariantCard";

// ---------------------------------------------------------------------------
// Metrics that are "higher is better" vs "lower is better"
// ---------------------------------------------------------------------------

const LOWER_IS_BETTER: Set<string> = new Set([
  "unsubscribe_rate",
  "cost_per_click",
  "bounce_rate",
  "opt_out_rate",
]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatMetricLabel(type: string): string {
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatMetricValue(value: number): string {
  if (value >= 1000)
    return value.toLocaleString("en-US", { maximumFractionDigits: 0 });
  if (value < 1) return (value * 100).toFixed(1) + "%";
  return value.toFixed(2);
}

/**
 * Determine the overall winner variant by counting how many metrics
 * each variant wins (using positive-direction logic).
 */
function computeWinner(
  variants: Variant[],
  metrics: MetricEntry[],
): string | null {
  if (metrics.length === 0 || variants.length < 2) return null;

  // Compute average per variant per metric type
  const avgs: Record<string, Record<string, { sum: number; count: number }>> =
    {};
  for (const m of metrics) {
    if (!avgs[m.variant_id]) avgs[m.variant_id] = {};
    if (!avgs[m.variant_id][m.metric_type]) {
      avgs[m.variant_id][m.metric_type] = { sum: 0, count: 0 };
    }
    avgs[m.variant_id][m.metric_type].sum += m.value;
    avgs[m.variant_id][m.metric_type].count += 1;
  }

  // Collect all metric types
  const metricTypes = new Set<string>();
  for (const variantAvgs of Object.values(avgs)) {
    for (const mt of Object.keys(variantAvgs)) {
      metricTypes.add(mt);
    }
  }

  // Count wins per variant
  const wins: Record<string, number> = {};
  for (const mt of metricTypes) {
    let bestId: string | null = null;
    let bestAvg = -Infinity;

    for (const [vid, variantAvgs] of Object.entries(avgs)) {
      if (!variantAvgs[mt]) continue;
      const avg = variantAvgs[mt].sum / variantAvgs[mt].count;
      const effectiveAvg = LOWER_IS_BETTER.has(mt) ? -avg : avg;

      if (effectiveAvg > bestAvg) {
        bestAvg = effectiveAvg;
        bestId = vid;
      }
    }

    if (bestId) {
      wins[bestId] = (wins[bestId] ?? 0) + 1;
    }
  }

  // Find the variant with the most wins
  let winnerId: string | null = null;
  let maxWins = 0;
  for (const [vid, count] of Object.entries(wins)) {
    if (count > maxWins) {
      maxWins = count;
      winnerId = vid;
    }
  }

  return winnerId;
}

// ---------------------------------------------------------------------------
// Metrics Table
// ---------------------------------------------------------------------------

interface MetricsTableProps {
  variants: Variant[];
  metrics: MetricEntry[];
}

function MetricsTable({ variants, metrics }: MetricsTableProps) {
  // Compute averages: variant_id -> metric_type -> average
  const { metricTypes, averages } = useMemo(() => {
    const raw: Record<
      string,
      Record<string, { sum: number; count: number }>
    > = {};
    const types = new Set<MetricType>();

    for (const m of metrics) {
      types.add(m.metric_type);
      if (!raw[m.variant_id]) raw[m.variant_id] = {};
      if (!raw[m.variant_id][m.metric_type]) {
        raw[m.variant_id][m.metric_type] = { sum: 0, count: 0 };
      }
      raw[m.variant_id][m.metric_type].sum += m.value;
      raw[m.variant_id][m.metric_type].count += 1;
    }

    const computed: Record<string, Record<string, number>> = {};
    for (const [vid, byType] of Object.entries(raw)) {
      computed[vid] = {};
      for (const [mt, { sum, count }] of Object.entries(byType)) {
        computed[vid][mt] = sum / count;
      }
    }

    return { metricTypes: Array.from(types).sort(), averages: computed };
  }, [metrics]);

  // For each metric type, find best and worst variant
  const bestWorst = useMemo(() => {
    const result: Record<string, { best: string | null; worst: string | null }> =
      {};

    for (const mt of metricTypes) {
      let bestId: string | null = null;
      let worstId: string | null = null;
      let bestVal = -Infinity;
      let worstVal = Infinity;

      const lowerBetter = LOWER_IS_BETTER.has(mt);

      for (const [vid, byType] of Object.entries(averages)) {
        if (byType[mt] === undefined) continue;
        const val = byType[mt];

        const effectiveVal = lowerBetter ? -val : val;
        if (effectiveVal > bestVal) {
          bestVal = effectiveVal;
          bestId = vid;
        }
        if (effectiveVal < worstVal) {
          worstVal = effectiveVal;
          worstId = vid;
        }
      }

      // Only mark best/worst if there are at least 2 variants with data
      const variantsWithData = Object.entries(averages).filter(
        ([, byType]) => byType[mt] !== undefined,
      );
      result[mt] = {
        best: variantsWithData.length >= 2 ? bestId : null,
        worst: variantsWithData.length >= 2 ? worstId : null,
      };
    }

    return result;
  }, [metricTypes, averages]);

  const variantIds = variants.map((v) => v.variant_id);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm" role="table">
        <thead>
          <tr className="border-b border-border">
            <th
              className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-muted"
              scope="col"
            >
              Metric
            </th>
            {variantIds.map((vid) => (
              <th
                key={vid}
                className="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-muted"
                scope="col"
              >
                {vid}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {metricTypes.map((mt) => (
            <tr
              key={mt}
              className="border-b border-border-subtle transition-colors duration-fast hover:bg-elevated/30"
            >
              <td className="px-4 py-3 font-medium text-foreground-secondary">
                {formatMetricLabel(mt)}
              </td>
              {variantIds.map((vid) => {
                const val = averages[vid]?.[mt];
                const isBest = bestWorst[mt]?.best === vid;
                const isWorst = bestWorst[mt]?.worst === vid;

                return (
                  <td
                    key={vid}
                    className={`px-4 py-3 text-right font-mono text-sm ${
                      isBest
                        ? "font-semibold text-success"
                        : isWorst
                          ? "text-error"
                          : "text-foreground"
                    }`}
                  >
                    {val !== undefined ? formatMetricValue(val) : "--"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton for detail page
// ---------------------------------------------------------------------------

function DetailSkeleton() {
  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10" aria-label="Loading campaign" role="status">
      <div className="skeleton mb-6 h-4 w-24 rounded" />
      <div className="skeleton mb-2 h-8 w-2/3 rounded" />
      <div className="mb-8 flex gap-2">
        <div className="skeleton h-5 w-14 rounded-badge" />
        <div className="skeleton h-5 w-20 rounded-badge" />
      </div>
      <div className="skeleton mb-4 h-5 w-16 rounded" />
      <div className="skeleton mb-2 h-4 w-full rounded" />
      <div className="skeleton mb-2 h-4 w-5/6 rounded" />
      <div className="skeleton mb-8 h-4 w-3/4 rounded" />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="skeleton h-48 rounded-card" />
        <div className="skeleton h-48 rounded-card" />
      </div>
      <span className="sr-only">Loading campaign details...</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Campaign Detail Page
// ---------------------------------------------------------------------------

export default function CampaignDetailPage() {
  const params = useParams();
  const id = typeof params.id === "string" ? params.id : undefined;
  const { campaign, isLoading, error } = useCampaign(id);

  // Determine winner variant
  const winnerId = useMemo(() => {
    if (!campaign) return null;
    return computeWinner(campaign.variants, campaign.metrics);
  }, [campaign]);

  // Group metrics by variant_id
  const metricsByVariant = useMemo(() => {
    if (!campaign) return {};
    const grouped: Record<string, MetricEntry[]> = {};
    for (const m of campaign.metrics) {
      if (!grouped[m.variant_id]) grouped[m.variant_id] = [];
      grouped[m.variant_id].push(m);
    }
    return grouped;
  }, [campaign]);

  // Loading
  if (isLoading) {
    return <DetailSkeleton />;
  }

  // Error
  if (error) {
    return (
      <div className="animate-fade-in px-6 py-8 lg:px-10">
        <Link
          href="/campaigns"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-foreground-secondary transition-colors duration-fast hover:text-accent"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M10 12L6 8l4-4" />
          </svg>
          Back to Campaigns
        </Link>
        <div
          className="mt-4 rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error"
          role="alert"
        >
          {error}
        </div>
      </div>
    );
  }

  // Not found (no error but no campaign)
  if (!campaign) {
    return (
      <div className="animate-fade-in px-6 py-8 lg:px-10">
        <Link
          href="/campaigns"
          className="mb-6 inline-flex items-center gap-1.5 text-sm text-foreground-secondary transition-colors duration-fast hover:text-accent"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M10 12L6 8l4-4" />
          </svg>
          Back to Campaigns
        </Link>
        <p className="mt-4 text-muted">Campaign not found.</p>
      </div>
    );
  }

  const { brief, variants, metrics } = campaign;

  const formattedDate = new Date(brief.created_at).toLocaleDateString(
    "en-US",
    {
      weekday: "long",
      month: "long",
      day: "numeric",
      year: "numeric",
    },
  );

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      {/* Back link */}
      <Link
        href="/campaigns"
        className="mb-6 inline-flex items-center gap-1.5 text-sm text-foreground-secondary transition-colors duration-fast hover:text-accent"
      >
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M10 12L6 8l4-4" />
        </svg>
        Back to Campaigns
      </Link>

      {/* ================================================================= */}
      {/* Header                                                             */}
      {/* ================================================================= */}
      <header className="mb-8">
        <div className="mb-3 flex flex-wrap items-center gap-3">
          <h1 className="font-display text-2xl font-bold text-foreground">
            {brief.campaign_name}
          </h1>
          <ChannelBadge channel={brief.channel} />
          <StatusBadge status={brief.status} />
        </div>
        <time dateTime={brief.created_at} className="text-sm text-muted">
          {formattedDate}
        </time>
      </header>

      {/* ================================================================= */}
      {/* Brief                                                              */}
      {/* ================================================================= */}
      <section className="mb-10" aria-labelledby="brief-heading">
        <h2
          id="brief-heading"
          className="mb-3 text-lg font-semibold text-foreground"
        >
          Brief
        </h2>
        <div className="rounded-card border border-border bg-surface p-5">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground-secondary">
            {brief.brief}
          </p>
        </div>
      </section>

      {/* ================================================================= */}
      {/* Variants                                                           */}
      {/* ================================================================= */}
      <section className="mb-10" aria-labelledby="variants-heading">
        <h2
          id="variants-heading"
          className="mb-3 text-lg font-semibold text-foreground"
        >
          Variants
          <span className="ml-2 text-sm font-normal text-muted">
            ({variants.length})
          </span>
        </h2>
        {variants.length === 0 ? (
          <p className="text-sm text-muted">
            No variants generated yet. Ask the agent to generate copy for this
            campaign.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {variants.map((variant) => (
              <VariantCard
                key={variant.variant_id}
                variant={variant}
                isWinner={winnerId === variant.variant_id}
                metrics={metricsByVariant[variant.variant_id]}
              />
            ))}
          </div>
        )}
      </section>

      {/* ================================================================= */}
      {/* Metrics                                                            */}
      {/* ================================================================= */}
      <section aria-labelledby="metrics-heading">
        <h2
          id="metrics-heading"
          className="mb-3 text-lg font-semibold text-foreground"
        >
          Metrics
        </h2>
        {metrics.length > 0 ? (
          <div className="rounded-card border border-border bg-surface shadow-card">
            <MetricsTable variants={variants} metrics={metrics} />
          </div>
        ) : (
          <div className="rounded-card border border-border-subtle bg-surface/50 px-6 py-10 text-center">
            <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-elevated">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-muted"
                aria-hidden="true"
              >
                <path d="M3 3v18h18" />
                <path d="M7 16l4-8 4 4 4-6" />
              </svg>
            </div>
            <p className="text-sm text-muted">
              No metrics logged yet. Share performance data in the chat to start
              analyzing.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
