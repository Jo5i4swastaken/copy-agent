"use client";

import { useState, useMemo } from "react";
import { usePlaybook } from "@/hooks/usePlaybook";
import type { PlaybookEntry, PlaybookCategory } from "@/lib/types";
import { LearningCard, LearningCardSkeleton } from "@/components/playbook/LearningCard";
import { CategoryFilter } from "@/components/playbook/CategoryFilter";
import { ConfidenceBar } from "@/components/playbook/ConfidenceBar";

// ---------------------------------------------------------------------------
// Sort modes
// ---------------------------------------------------------------------------

type SortMode = "confidence" | "date" | "confirmed";

const SORT_LABELS: Record<SortMode, string> = {
  confidence: "Confidence",
  date: "Newest",
  confirmed: "Most Confirmed",
};

const CATEGORIES: PlaybookCategory[] = ["email", "sms", "seo", "ad", "general"];

// ---------------------------------------------------------------------------
// PlaybookPage
// ---------------------------------------------------------------------------

export default function PlaybookPage() {
  const [activeCategory, setActiveCategory] = useState<string>("all");
  const [sortMode, setSortMode] = useState<SortMode>("confidence");

  // Fetch playbook — pass category filter to the hook (except "all")
  const filterCategory = activeCategory === "all" ? undefined : activeCategory;
  const { playbook, isLoading, error } = usePlaybook(filterCategory);

  // Sort entries client-side
  const sortedEntries = useMemo(() => {
    if (!playbook?.learnings) return [];

    const entries = [...playbook.learnings];

    switch (sortMode) {
      case "confidence":
        entries.sort((a, b) => b.confidence - a.confidence);
        break;
      case "date":
        entries.sort(
          (a, b) =>
            new Date(b.last_confirmed).getTime() - new Date(a.last_confirmed).getTime()
        );
        break;
      case "confirmed":
        entries.sort((a, b) => b.times_confirmed - a.times_confirmed);
        break;
    }

    return entries;
  }, [playbook?.learnings, sortMode]);

  // Compute stats from full playbook data
  const stats = useMemo(() => {
    const learnings = playbook?.learnings ?? [];
    const total = learnings.length;

    if (total === 0) {
      return { total: 0, avgConfidence: 0, byCategory: {} as Record<string, number> };
    }

    const avgConfidence =
      learnings.reduce((sum, e) => sum + e.confidence, 0) / total;

    const byCategory: Record<string, number> = {};
    for (const entry of learnings) {
      byCategory[entry.category] = (byCategory[entry.category] ?? 0) + 1;
    }

    return { total, avgConfidence, byCategory };
  }, [playbook?.learnings]);

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-foreground">
          Playbook
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Accumulated learnings that make your copy better over time
        </p>
      </div>

      {/* Stats summary */}
      {!isLoading && !error && stats.total > 0 && (
        <div className="mb-8 bg-surface rounded-card border border-border-subtle p-5 shadow-card">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {/* Total learnings */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted font-medium uppercase tracking-wide">
                Total Learnings
              </span>
              <span className="text-kpi-sm font-display text-foreground">
                {stats.total}
              </span>
            </div>

            {/* Avg confidence */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted font-medium uppercase tracking-wide">
                Avg Confidence
              </span>
              <div className="mt-1">
                <ConfidenceBar confidence={stats.avgConfidence} />
              </div>
            </div>

            {/* Category breakdown — horizontal stacked bar */}
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted font-medium uppercase tracking-wide">
                By Category
              </span>
              <div className="flex items-center gap-0.5 h-3 mt-1.5 rounded-full overflow-hidden bg-elevated">
                {CATEGORIES.map((cat) => {
                  const count = stats.byCategory[cat] ?? 0;
                  if (count === 0) return null;
                  const pct = (count / stats.total) * 100;
                  const colorMap: Record<string, string> = {
                    email: "bg-channel-email",
                    sms: "bg-channel-sms",
                    seo: "bg-channel-seo",
                    ad: "bg-channel-ad",
                    general: "bg-muted",
                  };
                  return (
                    <div
                      key={cat}
                      className={`h-full ${colorMap[cat] ?? "bg-muted"}`}
                      style={{ width: `${pct}%` }}
                      title={`${cat}: ${count}`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
                {CATEGORIES.map((cat) => {
                  const count = stats.byCategory[cat] ?? 0;
                  if (count === 0) return null;
                  const dotColorMap: Record<string, string> = {
                    email: "bg-channel-email",
                    sms: "bg-channel-sms",
                    seo: "bg-channel-seo",
                    ad: "bg-channel-ad",
                    general: "bg-muted",
                  };
                  return (
                    <span key={cat} className="flex items-center gap-1 text-xs text-muted">
                      <span className={`w-2 h-2 rounded-full ${dotColorMap[cat]}`} />
                      {cat.charAt(0).toUpperCase() + cat.slice(1)} ({count})
                    </span>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Filter bar + sort */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <CategoryFilter
          categories={CATEGORIES}
          active={activeCategory}
          onChange={setActiveCategory}
        />

        <div className="flex items-center gap-2">
          <span className="text-xs text-muted font-medium">Sort by:</span>
          <div className="flex items-center gap-1">
            {(Object.keys(SORT_LABELS) as SortMode[]).map((mode) => (
              <button
                key={mode}
                onClick={() => setSortMode(mode)}
                className={`
                  px-2.5 py-1 rounded-badge text-xs font-medium transition-colors duration-fast
                  focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
                  ${
                    sortMode === mode
                      ? "bg-accent/15 text-accent"
                      : "text-muted hover:text-foreground-secondary hover:bg-elevated"
                  }
                `}
              >
                {SORT_LABELS[mode]}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {Array.from({ length: 6 }).map((_, i) => (
            <LearningCardSkeleton key={i} />
          ))}
        </div>
      )}

      {error && (
        <div className="bg-error-muted border border-error/20 rounded-card p-6 text-center">
          <p className="text-error text-sm font-medium">Failed to load playbook</p>
          <p className="text-muted text-xs mt-1">{error}</p>
        </div>
      )}

      {!isLoading && !error && sortedEntries.length === 0 && (
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
                d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
              />
            </svg>
          </div>
          <p className="text-foreground font-medium text-sm">No learnings yet</p>
          <p className="text-muted text-xs mt-1">
            Run campaigns and analyze results to build your playbook.
          </p>
        </div>
      )}

      {!isLoading && !error && sortedEntries.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {sortedEntries.map((entry) => (
            <LearningCard key={entry.id} entry={entry} />
          ))}
        </div>
      )}
    </div>
  );
}
