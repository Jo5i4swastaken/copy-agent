"use client";

import Link from "next/link";
import type { CampaignSummary } from "@/lib/types";
import { ChannelBadge } from "./ChannelBadge";
import { StatusBadge } from "./StatusBadge";

// ---------------------------------------------------------------------------
// CampaignCard — clickable card for the campaign list page
// ---------------------------------------------------------------------------

interface CampaignCardProps {
  campaign: CampaignSummary;
}

export function CampaignCard({ campaign }: CampaignCardProps) {
  const formattedDate = new Date(campaign.created_at).toLocaleDateString(
    "en-US",
    {
      month: "short",
      day: "numeric",
      year: "numeric",
    },
  );

  return (
    <Link
      href={`/campaigns/${encodeURIComponent(campaign.campaign_id)}`}
      className="group block rounded-card border border-border bg-surface p-5 shadow-card transition-all duration-normal hover:border-border/80 hover:bg-elevated/50 hover:shadow-card-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      aria-label={`View campaign: ${campaign.campaign_name}`}
    >
      {/* Header row: badges + date */}
      <div className="mb-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <ChannelBadge channel={campaign.channel} />
          <StatusBadge status={campaign.status} />
        </div>
        <time
          dateTime={campaign.created_at}
          className="flex-shrink-0 text-xs text-muted"
        >
          {formattedDate}
        </time>
      </div>

      {/* Campaign name */}
      <h3 className="mb-2 text-base font-semibold text-foreground transition-colors duration-fast group-hover:text-accent">
        {campaign.campaign_name}
      </h3>

      {/* Variant count */}
      <div className="flex items-center gap-1.5 text-sm text-foreground-secondary">
        <svg
          width="14"
          height="14"
          viewBox="0 0 14 14"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M2 3.5h10M2 7h10M2 10.5h6" />
        </svg>
        <span>
          {campaign.num_variants} variant{campaign.num_variants !== 1 ? "s" : ""}
        </span>
      </div>
    </Link>
  );
}
