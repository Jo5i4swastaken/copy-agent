"use client";

import React, { useMemo } from "react";
import Link from "next/link";
import { useCampaigns } from "@/hooks/useCampaigns";
import { usePlaybook } from "@/hooks/usePlaybook";
import { useMetrics } from "@/hooks/useMetrics";
import { useABTests } from "@/hooks/useABTests";
import { OverviewCard, OverviewCardSkeleton } from "@/components/dashboard/OverviewCards";
import { RecentCampaigns, RecentCampaignsSkeleton } from "@/components/dashboard/RecentCampaigns";
import type { PlaybookEntry, PlaybookCategory } from "@/lib/types";

// =============================================================================
// Dashboard Overview Page
// =============================================================================

export default function DashboardPage() {
  const { campaigns, isLoading: campaignsLoading, error: campaignsError } = useCampaigns();
  const { playbook, isLoading: playbookLoading, error: playbookError } = usePlaybook();
  const { metrics, isLoading: metricsLoading, error: metricsError } = useMetrics();
  const { tests, isLoading: testsLoading, error: testsError } = useABTests();

  const activeTestCount = useMemo(() => {
    return tests.filter((t) =>
      ["COLLECTING", "WAITING", "ANALYZING", "DEPLOYING"].includes(t.state)
    ).length;
  }, [tests]);

  // -------------------------------------------------------------------------
  // Derived KPI values
  // -------------------------------------------------------------------------

  const activeCampaignCount = useMemo(() => {
    return campaigns.filter(
      (c) => c.status === "active" || c.status === "draft",
    ).length;
  }, [campaigns]);

  const totalVariants = useMemo(() => {
    return campaigns.reduce((sum, c) => sum + c.num_variants, 0);
  }, [campaigns]);

  const playbookLearnings = playbook?.learnings?.length ?? 0;

  const avgConfidence = useMemo(() => {
    if (!playbook?.learnings?.length) return null;
    const sum = playbook.learnings.reduce((acc, l) => acc + l.confidence, 0);
    return sum / playbook.learnings.length;
  }, [playbook]);

  // -------------------------------------------------------------------------
  // Top playbook entries by confidence
  // -------------------------------------------------------------------------

  const topLearnings = useMemo(() => {
    if (!playbook?.learnings?.length) return [];
    return [...playbook.learnings]
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 5);
  }, [playbook]);

  const isLoading = campaignsLoading || playbookLoading || metricsLoading || testsLoading;
  const error = campaignsError || playbookError || metricsError || testsError;

  return (
    <div className="p-6 lg:p-8 max-w-7xl mx-auto animate-fade-in">
      {error && (
        <div className="mb-6 rounded-lg border border-border bg-surface p-4 text-sm text-foreground-secondary">
          <span className="font-medium text-foreground">Dashboard load issue:</span> {error}
        </div>
      )}
      {/* -------------------------------------------------------------------
          Page Header
          ------------------------------------------------------------------- */}
      <div className="mb-8">
        <h1 className="text-2xl font-display font-bold text-foreground">
          Dashboard
        </h1>
        <p className="text-foreground-secondary text-sm mt-1">
          Overview of your copy campaigns and optimization progress
        </p>
      </div>

      {/* -------------------------------------------------------------------
          KPI Cards — Top Row
          ------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {isLoading ? (
          <>
            <OverviewCardSkeleton />
            <OverviewCardSkeleton />
            <OverviewCardSkeleton />
            <OverviewCardSkeleton />
          </>
        ) : (
          <>
            <OverviewCard
              title="Active Campaigns"
              value={activeCampaignCount}
              subtitle={`${campaigns.length} total campaigns`}
              icon={
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M3.75 3v11.25A2.25 2.25 0 0 0 6 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0 1 18 16.5h-2.25m-7.5 0h7.5m-7.5 0-1 3m8.5-3 1 3m0 0 .5 1.5m-.5-1.5h-9.5m0 0-.5 1.5m.75-9 3-3 2.148 2.148A12.061 12.061 0 0 1 16.5 7.605"
                  />
                </svg>
              }
            />
            <OverviewCard
              title="Total Variants"
              value={totalVariants}
              subtitle="Across all campaigns"
              icon={
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.5a1.125 1.125 0 0 1-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 0 1 1.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 0 0-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 0 1-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125-1.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H9.75"
                  />
                </svg>
              }
            />
            <OverviewCard
              title="Playbook Learnings"
              value={playbookLearnings}
              subtitle="Knowledge base entries"
              icon={
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25"
                  />
                </svg>
              }
            />
            <OverviewCard
              title="Avg Confidence"
              value={avgConfidence !== null ? `${Math.round(avgConfidence * 100)}%` : "--"}
              subtitle="Playbook entry confidence"
              icon={
                <svg
                  className="w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={2}
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z"
                  />
                </svg>
              }
            />
            <Link href="/ab-tests" className="block">
              <OverviewCard
                title="Active A/B Tests"
                value={activeTestCount}
                subtitle={`${tests.length} total tests`}
                icon={
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    strokeWidth={2}
                    stroke="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3 7.5h7.5v13.5H3zM13.5 3H21v18h-7.5z"
                    />
                  </svg>
                }
              />
            </Link>
          </>
        )}
      </div>

      {/* -------------------------------------------------------------------
          Bottom Row — Recent Campaigns + Playbook Highlights
          ------------------------------------------------------------------- */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Campaigns */}
        {isLoading ? (
          <RecentCampaignsSkeleton />
        ) : (
          <RecentCampaigns campaigns={campaigns} />
        )}

        {/* Playbook Highlights */}
        {isLoading ? (
          <PlaybookHighlightsSkeleton />
        ) : (
          <PlaybookHighlights learnings={topLearnings} />
        )}
      </div>
    </div>
  );
}

// =============================================================================
// PlaybookHighlights — Top confidence learnings
// =============================================================================

const categoryConfig: Record<PlaybookCategory, { label: string; colorClass: string }> = {
  email:   { label: "Email",   colorClass: "bg-channel-email/15 text-channel-email" },
  sms:     { label: "SMS",     colorClass: "bg-channel-sms/15 text-channel-sms" },
  seo:     { label: "SEO",     colorClass: "bg-channel-seo/15 text-channel-seo" },
  ad:      { label: "Ad",      colorClass: "bg-channel-ad/15 text-channel-ad" },
  general: { label: "General", colorClass: "bg-accent/10 text-accent" },
};

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.7) return "bg-confidence-high";
  if (confidence >= 0.4) return "bg-confidence-medium";
  return "bg-confidence-low";
}

function PlaybookHighlights({ learnings }: { learnings: PlaybookEntry[] }) {
  return (
    <div className="bg-surface rounded-card shadow-card border border-border-subtle p-5 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-foreground font-display font-semibold text-base">
          Playbook Highlights
        </h2>
        <Link
          href="/playbook"
          className="text-accent text-sm font-medium hover:underline underline-offset-4"
        >
          View playbook
        </Link>
      </div>

      {learnings.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <svg
            className="w-10 h-10 text-muted/50 mb-3"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 18v-5.25m0 0a6.01 6.01 0 0 0 1.5-.189m-1.5.189a6.01 6.01 0 0 1-1.5-.189m3.75 7.478a12.06 12.06 0 0 1-4.5 0m3.75 2.383a14.406 14.406 0 0 1-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 1 0-7.517 0c.85.493 1.509 1.333 1.509 2.316V18"
            />
          </svg>
          <p className="text-muted text-sm max-w-xs">
            Playbook will populate as you run campaigns and analyze results.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {learnings.map((entry) => {
            const catConfig = categoryConfig[entry.category] ?? categoryConfig.general;
            return (
              <div
                key={entry.id}
                className="rounded-lg border border-border-subtle bg-background/50 p-3 flex flex-col gap-2"
              >
                <p className="text-foreground text-sm leading-snug line-clamp-2">
                  {entry.learning}
                </p>
                <div className="flex items-center gap-3">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-badge text-badge font-medium ${catConfig.colorClass}`}
                  >
                    {catConfig.label}
                  </span>
                  {/* Confidence bar */}
                  <div className="flex items-center gap-2 flex-1">
                    <div className="flex-1 h-1.5 rounded-full bg-elevated overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-slow ${getConfidenceColor(entry.confidence)}`}
                        style={{ width: `${Math.round(entry.confidence * 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-muted tabular-nums w-8 text-right">
                      {Math.round(entry.confidence * 100)}%
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// PlaybookHighlightsSkeleton
// =============================================================================

function PlaybookHighlightsSkeleton() {
  return (
    <div className="bg-surface rounded-card shadow-card border border-border-subtle p-5 flex flex-col animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div className="skeleton h-5 w-40 rounded" />
        <div className="skeleton h-4 w-24 rounded" />
      </div>
      <div className="flex flex-col gap-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="rounded-lg border border-border-subtle bg-background/50 p-3 flex flex-col gap-2"
          >
            <div className="skeleton h-4 w-full rounded" />
            <div className="skeleton h-3 w-3/4 rounded" />
            <div className="flex items-center gap-3">
              <div className="skeleton h-5 w-14 rounded-badge" />
              <div className="flex-1 skeleton h-1.5 rounded-full" />
              <div className="skeleton h-3 w-8 rounded" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
