"use client";

import { useState } from "react";
import type { PlaybookEntry, PlaybookCategory } from "@/lib/types";
import { ConfidenceBar } from "@/components/playbook/ConfidenceBar";

// ---------------------------------------------------------------------------
// LearningCard — Displays a single PlaybookEntry as a styled card
// ---------------------------------------------------------------------------

interface LearningCardProps {
  entry: PlaybookEntry;
}

// Category badge styling — uses channel design tokens
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

export function LearningCard({ entry }: LearningCardProps) {
  const [evidenceOpen, setEvidenceOpen] = useState(false);

  const categoryStyle = CATEGORY_STYLES[entry.category] ?? "bg-elevated text-muted";
  const categoryLabel = CATEGORY_LABELS[entry.category] ?? entry.category;

  const isFromSeed = entry.source === "seed" || entry.id.startsWith("seed_");

  return (
    <article
      className="bg-surface rounded-card shadow-card hover:shadow-card-hover transition-shadow duration-normal border border-border-subtle p-5 flex flex-col gap-4 animate-fade-in"
    >
      {/* Header: category badge + source badge */}
      <div className="flex items-center justify-between gap-2">
        <span
          className={`inline-flex items-center rounded-badge px-2 py-0.5 text-badge font-medium ${categoryStyle}`}
        >
          {categoryLabel}
        </span>
        <span
          className={`inline-flex items-center rounded-badge px-2 py-0.5 text-badge font-medium ${
            isFromSeed
              ? "bg-elevated text-muted"
              : "bg-accent/10 text-accent"
          }`}
        >
          {isFromSeed ? "Seed" : "Campaign"}
        </span>
      </div>

      {/* Learning text */}
      <p className="text-sm text-foreground leading-relaxed">
        {entry.learning}
      </p>

      {/* Confidence bar */}
      <div className="flex flex-col gap-1">
        <span className="text-xs text-muted font-medium">Confidence</span>
        <ConfidenceBar confidence={entry.confidence} />
      </div>

      {/* Confirmed / Contradicted counts */}
      <div className="flex items-center gap-4 text-xs font-medium">
        <span className="flex items-center gap-1 text-success">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="w-3.5 h-3.5"
            aria-hidden="true"
          >
            <path
              fillRule="evenodd"
              d="M12.416 3.376a.75.75 0 0 1 .208 1.04l-5 7.5a.75.75 0 0 1-1.154.114l-3-3a.75.75 0 0 1 1.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 0 1 1.04-.207Z"
              clipRule="evenodd"
            />
          </svg>
          {entry.times_confirmed} confirmed
        </span>
        <span className="flex items-center gap-1 text-error">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 16 16"
            fill="currentColor"
            className="w-3.5 h-3.5"
            aria-hidden="true"
          >
            <path
              d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
            />
          </svg>
          {entry.times_contradicted} contradicted
        </span>
      </div>

      {/* Tags */}
      {entry.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
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

      {/* Evidence (collapsible) */}
      {entry.evidence && (
        <div className="border-t border-border-subtle pt-3">
          <button
            onClick={() => setEvidenceOpen((prev) => !prev)}
            className="flex items-center gap-1.5 text-xs text-foreground-secondary hover:text-foreground transition-colors duration-fast"
            aria-expanded={evidenceOpen}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 16 16"
              fill="currentColor"
              className={`w-3.5 h-3.5 transition-transform duration-fast ${
                evidenceOpen ? "rotate-90" : ""
              }`}
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                d="M6.22 4.22a.75.75 0 0 1 1.06 0l3.25 3.25a.75.75 0 0 1 0 1.06l-3.25 3.25a.75.75 0 0 1-1.06-1.06L8.94 8 6.22 5.28a.75.75 0 0 1 0-1.06Z"
                clipRule="evenodd"
              />
            </svg>
            Evidence
          </button>
          {evidenceOpen && (
            <p className="mt-2 text-xs text-muted leading-relaxed pl-5">
              {entry.evidence}
            </p>
          )}
        </div>
      )}
    </article>
  );
}

// ---------------------------------------------------------------------------
// LearningCardSkeleton — Loading placeholder
// ---------------------------------------------------------------------------

export function LearningCardSkeleton() {
  return (
    <div className="bg-surface rounded-card shadow-card border border-border-subtle p-5 flex flex-col gap-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="skeleton h-5 w-16 rounded-badge" />
        <div className="skeleton h-5 w-20 rounded-badge" />
      </div>
      <div className="flex flex-col gap-1.5">
        <div className="skeleton h-4 w-full rounded" />
        <div className="skeleton h-4 w-3/4 rounded" />
      </div>
      <div className="flex flex-col gap-1">
        <div className="skeleton h-3 w-16 rounded" />
        <div className="skeleton h-2 w-full rounded-full" />
      </div>
      <div className="flex items-center gap-4">
        <div className="skeleton h-3 w-24 rounded" />
        <div className="skeleton h-3 w-28 rounded" />
      </div>
      <div className="flex gap-1.5">
        <div className="skeleton h-5 w-14 rounded-full" />
        <div className="skeleton h-5 w-18 rounded-full" />
        <div className="skeleton h-5 w-12 rounded-full" />
      </div>
    </div>
  );
}
