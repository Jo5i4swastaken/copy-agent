"use client";

import type { Channel } from "@/lib/types";

// ---------------------------------------------------------------------------
// Channel color mapping — uses design tokens from tailwind.config.ts
// ---------------------------------------------------------------------------

const CHANNEL_STYLES: Record<Channel, string> = {
  email: "bg-channel-email/15 text-channel-email",
  sms: "bg-channel-sms/15 text-channel-sms",
  seo: "bg-channel-seo/15 text-channel-seo",
  ad: "bg-channel-ad/15 text-channel-ad",
};

const CHANNEL_LABELS: Record<Channel, string> = {
  email: "Email",
  sms: "SMS",
  seo: "SEO",
  ad: "Ad",
};

// ---------------------------------------------------------------------------
// ChannelBadge
// ---------------------------------------------------------------------------

interface ChannelBadgeProps {
  channel: Channel;
}

export function ChannelBadge({ channel }: ChannelBadgeProps) {
  const styles = CHANNEL_STYLES[channel] ?? "bg-elevated text-muted";
  const label = CHANNEL_LABELS[channel] ?? channel.toUpperCase();

  return (
    <span
      className={`inline-flex items-center rounded-badge px-2 py-0.5 text-badge font-medium ${styles}`}
    >
      {label}
    </span>
  );
}
