"use client";

import React from "react";
import Link from "next/link";
import type { CampaignSummary, Channel } from "@/lib/types";

// ---------------------------------------------------------------------------
// Channel badge — colored pill using channel-* design tokens
// ---------------------------------------------------------------------------

const channelConfig: Record<Channel, { label: string; colorClass: string }> = {
  email: { label: "Email", colorClass: "bg-channel-email/15 text-channel-email" },
  sms:   { label: "SMS",   colorClass: "bg-channel-sms/15 text-channel-sms" },
  seo:   { label: "SEO",   colorClass: "bg-channel-seo/15 text-channel-seo" },
  ad:    { label: "Ad",    colorClass: "bg-channel-ad/15 text-channel-ad" },
};

function ChannelBadge({ channel }: { channel: Channel }) {
  const config = channelConfig[channel];
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-badge text-badge font-medium ${config.colorClass}`}
    >
      {config.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// RecentCampaigns — List of recent campaigns for the dashboard overview
// ---------------------------------------------------------------------------

interface RecentCampaignsProps {
  campaigns: CampaignSummary[];
}

/**
 * Displays a list of recent campaigns with name, channel badge,
 * creation date, and variant count. Limits display to the 5 most recent.
 */
export function RecentCampaigns({ campaigns }: RecentCampaignsProps) {
  const recentCampaigns = campaigns
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(0, 5);

  return (
    <div className="bg-surface rounded-card shadow-card border border-border-subtle p-5 flex flex-col">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-foreground font-display font-semibold text-base">
          Recent Campaigns
        </h2>
        <Link
          href="/campaigns"
          className="text-accent text-sm font-medium hover:underline underline-offset-4"
        >
          View all
        </Link>
      </div>

      {recentCampaigns.length === 0 ? (
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
              d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
            />
          </svg>
          <p className="text-muted text-sm max-w-xs">
            No campaigns yet. Use the chat panel to create your first campaign.
          </p>
        </div>
      ) : (
        <div className="flex flex-col divide-y divide-border-subtle">
          {recentCampaigns.map((campaign) => (
            <div
              key={campaign.campaign_id}
              className="flex items-center gap-3 py-3 first:pt-0 last:pb-0"
            >
              <div className="flex-1 min-w-0">
                <p className="text-foreground text-sm font-medium truncate">
                  {campaign.campaign_name}
                </p>
                <p className="text-muted text-xs mt-0.5">
                  {formatDate(campaign.created_at)}
                </p>
              </div>
              <ChannelBadge channel={campaign.channel} />
              <span className="text-foreground-secondary text-sm tabular-nums whitespace-nowrap">
                {campaign.num_variants}{" "}
                <span className="text-muted">
                  {campaign.num_variants === 1 ? "variant" : "variants"}
                </span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// RecentCampaignsSkeleton — Loading placeholder
// ---------------------------------------------------------------------------

export function RecentCampaignsSkeleton() {
  return (
    <div className="bg-surface rounded-card shadow-card border border-border-subtle p-5 flex flex-col animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <div className="skeleton h-5 w-40 rounded" />
        <div className="skeleton h-4 w-16 rounded" />
      </div>
      <div className="flex flex-col divide-y divide-border-subtle">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            <div className="flex-1 min-w-0">
              <div className="skeleton h-4 w-48 rounded mb-1.5" />
              <div className="skeleton h-3 w-24 rounded" />
            </div>
            <div className="skeleton h-5 w-12 rounded-badge" />
            <div className="skeleton h-4 w-20 rounded" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateString: string): string {
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return dateString;
  }
}
