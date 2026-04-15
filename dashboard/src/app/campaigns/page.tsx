"use client";

import { useState, useMemo } from "react";
import type { Channel } from "@/lib/types";
import { useCampaigns } from "@/hooks/useCampaigns";
import { CampaignCard } from "@/components/campaigns/CampaignCard";

// ---------------------------------------------------------------------------
// Filter options
// ---------------------------------------------------------------------------

const CHANNEL_OPTIONS: { label: string; value: Channel | "" }[] = [
  { label: "All Channels", value: "" },
  { label: "Email", value: "email" },
  { label: "SMS", value: "sms" },
  { label: "SEO", value: "seo" },
  { label: "Ads", value: "ad" },
];

const STATUS_OPTIONS: { label: string; value: string }[] = [
  { label: "All Statuses", value: "" },
  { label: "Active", value: "active" },
  { label: "Draft", value: "draft" },
  { label: "Completed", value: "complete" },
];

// ---------------------------------------------------------------------------
// Skeleton card for loading state
// ---------------------------------------------------------------------------

function SkeletonCard() {
  return (
    <div
      className="rounded-card border border-border bg-surface p-5 shadow-card"
      aria-hidden="true"
    >
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="skeleton h-5 w-14 rounded-badge" />
          <div className="skeleton h-5 w-16 rounded-badge" />
        </div>
        <div className="skeleton h-4 w-20 rounded" />
      </div>
      <div className="skeleton mb-2 h-5 w-3/4 rounded" />
      <div className="skeleton mb-3 h-4 w-full rounded" />
      <div className="skeleton h-4 w-2/3 rounded" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Campaigns List Page
// ---------------------------------------------------------------------------

export default function CampaignsPage() {
  const [channelFilter, setChannelFilter] = useState<Channel | "">("");
  const [statusFilter, setStatusFilter] = useState("");

  const filters = useMemo(
    () => ({
      channel: channelFilter || undefined,
      status: statusFilter || undefined,
    }),
    [channelFilter, statusFilter],
  );

  const { campaigns, isLoading, error } = useCampaigns(filters);

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-foreground">
          Campaigns
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Browse and manage your marketing copy campaigns.
        </p>
      </div>

      {/* Filter bar */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label className="sr-only" htmlFor="channel-filter">
          Filter by channel
        </label>
        <select
          id="channel-filter"
          value={channelFilter}
          onChange={(e) => setChannelFilter(e.target.value as Channel | "")}
          className="rounded-badge border border-border bg-surface px-3 py-2 text-sm text-foreground transition-colors duration-fast hover:border-foreground-secondary/30 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {CHANNEL_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <label className="sr-only" htmlFor="status-filter">
          Filter by status
        </label>
        <select
          id="status-filter"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="rounded-badge border border-border bg-surface px-3 py-2 text-sm text-foreground transition-colors duration-fast hover:border-foreground-secondary/30 focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {STATUS_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Error state */}
      {error && (
        <div
          className="mb-6 rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div
          className="grid grid-cols-1 gap-4 lg:grid-cols-2"
          aria-label="Loading campaigns"
          role="status"
        >
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
          <span className="sr-only">Loading campaigns...</span>
        </div>
      )}

      {/* Campaign grid */}
      {!isLoading && !error && campaigns.length > 0 && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {campaigns.map((campaign) => (
            <CampaignCard key={campaign.campaign_id} campaign={campaign} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && campaigns.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-card border border-border-subtle bg-surface/50 px-6 py-16 text-center">
          <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-elevated">
            <svg
              width="28"
              height="28"
              viewBox="0 0 28 28"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-muted"
              aria-hidden="true"
            >
              <path d="M4 14V6a1.5 1.5 0 0 1 1.5-1.5H9l3 4.5h11A1.5 1.5 0 0 1 24.5 10.5v12a1.5 1.5 0 0 1-1.5 1.5H5.5A1.5 1.5 0 0 1 4 22.5V14z" />
            </svg>
          </div>
          <h2 className="mb-1 text-base font-semibold text-foreground">
            No campaigns found
          </h2>
          <p className="max-w-sm text-sm text-muted">
            Create your first campaign using the chat panel. Ask the agent to
            generate marketing copy for your product or service.
          </p>
        </div>
      )}
    </div>
  );
}
