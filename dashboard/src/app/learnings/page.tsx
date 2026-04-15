"use client";

import { useMemo } from "react";
import { usePlaybook } from "@/hooks/usePlaybook";
import type { PlaybookEntry, PlaybookCategory } from "@/lib/types";
import { ConfidenceBar } from "@/components/playbook/ConfidenceBar";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const CATEGORY_STYLES: Record<PlaybookCategory, string> = {
  email: "bg-channel-email/15 text-channel-email",
  sms: "bg-channel-sms/15 text-channel-sms",
  seo: "bg-channel-seo/15 text-channel-seo",
  ad: "bg-channel-ad/15 text-channel-ad",
  general: "bg-elevated text-foreground-secondary",
};

const CATEGORY_LABELS: Record<PlaybookCategory, string> = {
  email: "Email",
  sms: "SMS",
  seo: "SEO",
  ad: "Ad",
  general: "General",
};

function formatDate(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

function formatMonthKey(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
  } catch {
    return dateStr;
  }
}

// ---------------------------------------------------------------------------
// LearningsPage
// ---------------------------------------------------------------------------

export default function LearningsPage() {
  const { playbook, isLoading, error } = usePlaybook();

  // Build timeline data sorted by last_confirmed (newest first)
  const timelineEntries = useMemo(() => {
    if (!playbook?.learnings) return [];
    return [...playbook.learnings].sort(
      (a, b) =>
        new Date(b.last_confirmed).getTime() - new Date(a.last_confirmed).getTime()
    );
  }, [playbook?.learnings]);

  // Optimization progress stats
  const progressStats = useMemo(() => {
    const learnings = playbook?.learnings ?? [];
    const total = learnings.length;

    // Confidence distribution
    let low = 0;
    let medium = 0;
    let high = 0;
    for (const entry of learnings) {
      if (entry.confidence < 0.4) low++;
      else if (entry.confidence <= 0.7) medium++;
      else high++;
    }

    // Learnings per month
    const monthCounts: Record<string, number> = {};
    for (const entry of learnings) {
      const key = formatMonthKey(entry.first_observed);
      monthCounts[key] = (monthCounts[key] ?? 0) + 1;
    }

    // Top performing category — highest count of high-confidence learnings
    const highConfByCategory: Record<string, number> = {};
    for (const entry of learnings) {
      if (entry.confidence > 0.7) {
        highConfByCategory[entry.category] =
          (highConfByCategory[entry.category] ?? 0) + 1;
      }
    }
    let topCategory: string | null = null;
    let topCategoryCount = 0;
    for (const [cat, count] of Object.entries(highConfByCategory)) {
      if (count > topCategoryCount) {
        topCategory = cat;
        topCategoryCount = count;
      }
    }

    return {
      total,
      low,
      medium,
      high,
      monthCounts,
      topCategory,
      topCategoryCount,
    };
  }, [playbook?.learnings]);

  const hasData = timelineEntries.length > 0;

  return (
    <div className="p-6 lg:p-8 max-w-5xl mx-auto animate-fade-in">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-foreground">
          Learnings
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Track how your optimization insights evolve
        </p>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-6">
          {/* Stats skeleton */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
            {Array.from({ length: 3 }).map((_, i) => (
              <div
                key={i}
                className="bg-surface rounded-card border border-border-subtle p-5 flex flex-col gap-3"
              >
                <div className="skeleton h-3 w-24 rounded" />
                <div className="skeleton h-7 w-16 rounded" />
                <div className="skeleton h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
          {/* Timeline skeleton */}
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="skeleton w-3 h-3 rounded-full" />
                  <div className="skeleton w-0.5 flex-1 mt-1" />
                </div>
                <div className="bg-surface rounded-card border border-border-subtle p-4 flex-1">
                  <div className="skeleton h-3 w-24 rounded mb-3" />
                  <div className="skeleton h-4 w-full rounded mb-2" />
                  <div className="skeleton h-4 w-2/3 rounded" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="bg-error-muted border border-error/20 rounded-card p-6 text-center">
          <p className="text-error text-sm font-medium">Failed to load learnings</p>
          <p className="text-muted text-xs mt-1">{error}</p>
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && (
        <>
          {/* Optimization progress section */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-10">
            {/* Learnings Over Time */}
            <div className="bg-surface rounded-card border border-border-subtle p-5 shadow-card flex flex-col gap-3">
              <span className="text-xs text-muted font-medium uppercase tracking-wide">
                Learnings Over Time
              </span>
              {hasData ? (
                <>
                  <span className="text-kpi-sm font-display text-foreground">
                    {progressStats.total}
                  </span>
                  <div className="flex flex-wrap gap-x-3 gap-y-1">
                    {Object.entries(progressStats.monthCounts).map(([month, count]) => (
                      <span key={month} className="text-xs text-muted">
                        {month}: <span className="text-foreground-secondary font-medium">{count}</span>
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <span className="text-sm text-muted">No data yet</span>
              )}
            </div>

            {/* Confidence Distribution */}
            <div className="bg-surface rounded-card border border-border-subtle p-5 shadow-card flex flex-col gap-3">
              <span className="text-xs text-muted font-medium uppercase tracking-wide">
                Confidence Distribution
              </span>
              {hasData ? (
                <div className="flex flex-col gap-2.5 mt-1">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs">
                      <span className="w-2 h-2 rounded-full bg-confidence-high" />
                      <span className="text-foreground-secondary">High</span>
                    </span>
                    <span className="text-xs font-medium text-foreground tabular-nums">
                      {progressStats.high}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs">
                      <span className="w-2 h-2 rounded-full bg-confidence-medium" />
                      <span className="text-foreground-secondary">Medium</span>
                    </span>
                    <span className="text-xs font-medium text-foreground tabular-nums">
                      {progressStats.medium}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-xs">
                      <span className="w-2 h-2 rounded-full bg-confidence-low" />
                      <span className="text-foreground-secondary">Low</span>
                    </span>
                    <span className="text-xs font-medium text-foreground tabular-nums">
                      {progressStats.low}
                    </span>
                  </div>
                  {/* Visual mini bar */}
                  <div className="flex h-2 rounded-full overflow-hidden bg-elevated mt-1">
                    {progressStats.high > 0 && (
                      <div
                        className="bg-confidence-high h-full"
                        style={{
                          width: `${(progressStats.high / progressStats.total) * 100}%`,
                        }}
                      />
                    )}
                    {progressStats.medium > 0 && (
                      <div
                        className="bg-confidence-medium h-full"
                        style={{
                          width: `${(progressStats.medium / progressStats.total) * 100}%`,
                        }}
                      />
                    )}
                    {progressStats.low > 0 && (
                      <div
                        className="bg-confidence-low h-full"
                        style={{
                          width: `${(progressStats.low / progressStats.total) * 100}%`,
                        }}
                      />
                    )}
                  </div>
                </div>
              ) : (
                <span className="text-sm text-muted">No data yet</span>
              )}
            </div>

            {/* Top Performing Category */}
            <div className="bg-surface rounded-card border border-border-subtle p-5 shadow-card flex flex-col gap-3">
              <span className="text-xs text-muted font-medium uppercase tracking-wide">
                Top Performing Category
              </span>
              {progressStats.topCategory ? (
                <>
                  <span className="text-kpi-sm font-display text-foreground capitalize">
                    {CATEGORY_LABELS[progressStats.topCategory as PlaybookCategory] ??
                      progressStats.topCategory}
                  </span>
                  <span className="text-xs text-foreground-secondary">
                    {progressStats.topCategoryCount} high-confidence{" "}
                    {progressStats.topCategoryCount === 1 ? "learning" : "learnings"}
                  </span>
                </>
              ) : (
                <div className="flex flex-col gap-1">
                  <span className="text-sm text-muted">Not enough data</span>
                  <span className="text-xs text-muted">
                    Build high-confidence learnings to see your top category.
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Timeline */}
          {!hasData && (
            <div className="bg-surface rounded-card border border-border-subtle p-12 text-center">
              <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-elevated flex items-center justify-center">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.5}
                  className="w-6 h-6 text-muted"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5M9 11.25v1.5M12 9v3.75m3-6v6"
                  />
                </svg>
              </div>
              <p className="text-foreground font-medium text-sm">
                Your learning timeline will appear here
              </p>
              <p className="text-muted text-xs mt-1 max-w-md mx-auto">
                As you run campaigns and analyze results, the playbook grows automatically.
                Each insight gets stronger with repeated confirmation.
              </p>
            </div>
          )}

          {hasData && (
            <div>
              <h2 className="text-lg font-display font-semibold text-foreground mb-6">
                Timeline
              </h2>
              <div className="relative">
                {timelineEntries.map((entry, index) => {
                  const isLast = index === timelineEntries.length - 1;
                  const categoryStyle =
                    CATEGORY_STYLES[entry.category] ?? "bg-elevated text-muted";
                  const categoryLabel =
                    CATEGORY_LABELS[entry.category] ?? entry.category;

                  // Confidence change indicator: show up arrow if confirmed multiple times
                  const showConfidenceUp = entry.times_confirmed > 1;

                  return (
                    <div key={entry.id} className="flex gap-4 pb-6 last:pb-0">
                      {/* Timeline connector */}
                      <div className="flex flex-col items-center pt-1.5">
                        {/* Dot */}
                        <div
                          className={`w-3 h-3 rounded-full flex-shrink-0 ring-4 ring-background ${
                            entry.confidence > 0.7
                              ? "bg-confidence-high"
                              : entry.confidence >= 0.4
                                ? "bg-confidence-medium"
                                : "bg-confidence-low"
                          }`}
                        />
                        {/* Vertical line */}
                        {!isLast && (
                          <div className="w-0.5 flex-1 bg-border-subtle mt-1" />
                        )}
                      </div>

                      {/* Card content */}
                      <div className="flex-1 bg-surface rounded-card border border-border-subtle p-4 shadow-card hover:shadow-card-hover transition-shadow duration-normal min-w-0">
                        {/* Top row: date + category */}
                        <div className="flex items-center justify-between gap-2 mb-2">
                          <span className="text-xs text-muted font-medium">
                            {formatDate(entry.last_confirmed)}
                          </span>
                          <span
                            className={`inline-flex items-center rounded-badge px-2 py-0.5 text-badge font-medium ${categoryStyle}`}
                          >
                            {categoryLabel}
                          </span>
                        </div>

                        {/* Learning text */}
                        <p className="text-sm text-foreground leading-relaxed mb-3">
                          {entry.learning}
                        </p>

                        {/* Bottom row: confidence + indicators */}
                        <div className="flex items-center gap-4">
                          <div className="flex-1 max-w-[200px]">
                            <ConfidenceBar confidence={entry.confidence} />
                          </div>

                          {showConfidenceUp && (
                            <span className="flex items-center gap-0.5 text-xs font-medium text-success">
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 16 16"
                                fill="currentColor"
                                className="w-3 h-3"
                                aria-hidden="true"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M8 14a.75.75 0 0 1-.75-.75V4.56L4.03 7.78a.75.75 0 0 1-1.06-1.06l4.5-4.5a.75.75 0 0 1 1.06 0l4.5 4.5a.75.75 0 0 1-1.06 1.06L8.75 4.56v8.69A.75.75 0 0 1 8 14Z"
                                  clipRule="evenodd"
                                />
                              </svg>
                              Confirmed {entry.times_confirmed}x
                            </span>
                          )}

                          {entry.times_contradicted > 0 && (
                            <span className="flex items-center gap-0.5 text-xs font-medium text-error">
                              <svg
                                xmlns="http://www.w3.org/2000/svg"
                                viewBox="0 0 16 16"
                                fill="currentColor"
                                className="w-3 h-3"
                                aria-hidden="true"
                              >
                                <path
                                  fillRule="evenodd"
                                  d="M8 2a.75.75 0 0 1 .75.75v8.69l3.22-3.22a.75.75 0 1 1 1.06 1.06l-4.5 4.5a.75.75 0 0 1-1.06 0l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.22 3.22V2.75A.75.75 0 0 1 8 2Z"
                                  clipRule="evenodd"
                                />
                              </svg>
                              {entry.times_contradicted}x contradicted
                            </span>
                          )}
                        </div>

                        {/* Tags */}
                        {entry.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-3">
                            {entry.tags.map((tag) => (
                              <span
                                key={tag}
                                className="inline-flex items-center rounded-full bg-elevated px-2 py-0.5 text-xs text-muted"
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
