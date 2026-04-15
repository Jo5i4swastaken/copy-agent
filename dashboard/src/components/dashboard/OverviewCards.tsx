"use client";

import React from "react";

// ---------------------------------------------------------------------------
// OverviewCard — Reusable KPI card for the dashboard overview
// ---------------------------------------------------------------------------

interface OverviewCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  subtitle?: string;
}

/**
 * A single KPI card displaying a metric with an icon, label, and large value.
 *
 * Uses design-system tokens: bg-surface, rounded-card, shadow-card,
 * font-display for the value, and accent color for the icon.
 */
export function OverviewCard({ title, value, icon, subtitle }: OverviewCardProps) {
  return (
    <div className="bg-surface rounded-card shadow-card hover:shadow-card-hover transition-shadow duration-normal p-5 flex flex-col gap-3 border border-border-subtle">
      <div className="flex items-center justify-between">
        <span className="text-muted text-sm font-medium">{title}</span>
        <div className="text-accent w-8 h-8 flex items-center justify-center rounded-badge bg-accent/10">
          {icon}
        </div>
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-kpi-sm font-display text-foreground">{value}</span>
        {subtitle && (
          <span className="text-xs text-muted">{subtitle}</span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// OverviewCardSkeleton — Loading placeholder for KPI cards
// ---------------------------------------------------------------------------

/**
 * Skeleton loader matching the OverviewCard dimensions.
 * Shows a shimmer animation while data is being fetched.
 */
export function OverviewCardSkeleton() {
  return (
    <div className="bg-surface rounded-card shadow-card p-5 flex flex-col gap-3 border border-border-subtle animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="skeleton h-4 w-28 rounded" />
        <div className="skeleton h-8 w-8 rounded-badge" />
      </div>
      <div className="flex flex-col gap-1">
        <div className="skeleton h-7 w-20 rounded" />
        <div className="skeleton h-3 w-32 rounded" />
      </div>
    </div>
  );
}
