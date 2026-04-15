/**
 * Shared test fixtures for the Copy Agent dashboard tests.
 */

import type { CampaignSummary, Campaign, Brief, Variant, MetricEntry } from "@/lib/types";
import type { ABTestState, ABTestCheck } from "@/hooks/useABTests";
import type { ReportSummary, ReportDetail } from "@/hooks/useReports";

// ---------------------------------------------------------------------------
// Campaign fixtures
// ---------------------------------------------------------------------------

export const mockBrief: Brief = {
  campaign_id: "spring-sale",
  campaign_name: "Spring Sale",
  brief: "Promote our spring sale",
  channel: "email",
  num_variants: 2,
  created_at: "2026-04-01T10:00:00",
  status: "active",
};

export const mockVariants: Variant[] = [
  {
    variant_id: "v1",
    channel: "email",
    content: "Don't miss 30% off!",
    subject_line: "30% Off Everything",
    cta: "Shop Now",
    tone: "urgent",
    notes: "",
    created_at: "2026-04-01T10:05:00",
    status: "draft",
  },
  {
    variant_id: "v2",
    channel: "email",
    content: "Spring deals are here.",
    subject_line: "Fresh Deals for Spring",
    cta: "Browse Deals",
    tone: "playful",
    notes: "",
    created_at: "2026-04-01T10:06:00",
    status: "draft",
  },
];

export const mockMetrics: MetricEntry[] = [
  { variant_id: "v1", metric_type: "open_rate", value: 0.22, date: "2026-04-02", notes: "", logged_at: "2026-04-02T12:00:00" },
  { variant_id: "v2", metric_type: "open_rate", value: 0.31, date: "2026-04-02", notes: "", logged_at: "2026-04-02T12:00:00" },
];

export const mockCampaign: Campaign = {
  brief: mockBrief,
  variants: mockVariants,
  metrics: mockMetrics,
};

export const mockCampaignSummaries: CampaignSummary[] = [
  {
    campaign_id: "spring-sale",
    campaign_name: "Spring Sale",
    channel: "email",
    status: "active",
    created_at: "2026-04-01T10:00:00",
    num_variants: 2,
  },
  {
    campaign_id: "summer-promo-sms",
    campaign_name: "Summer Promo",
    channel: "sms",
    status: "draft",
    created_at: "2026-04-02T09:00:00",
    num_variants: 1,
  },
];

// ---------------------------------------------------------------------------
// A/B test fixtures
// ---------------------------------------------------------------------------

export const mockABTestCollecting: ABTestState = {
  test_id: "test-001",
  campaign_id: "spring-sale",
  state: "COLLECTING",
  hypothesis: "Playful tone beats urgent tone for open rates",
  control_variant_id: "v1",
  treatment_variant_id: "v2",
  metric_type: "open_rate",
  created_at: "2026-04-01T10:00:00",
  next_check_at: "2026-04-03T10:00:00",
  max_duration_hours: 336,
  checks: [],
  result: null,
};

export const mockABTestDecided: ABTestState = {
  test_id: "test-002",
  campaign_id: "spring-sale-2",
  state: "DECIDED",
  hypothesis: "Numbers in subject lines increase open rates",
  control_variant_id: "control",
  treatment_variant_id: "treatment",
  metric_type: "open_rate",
  created_at: "2026-03-28T10:00:00",
  next_check_at: null,
  max_duration_hours: 336,
  checks: [
    {
      check_number: 1,
      checked_at: "2026-04-01T10:00:00",
      control_value: 0.18,
      treatment_value: 0.29,
      p_value: 0.003,
      effect_size: 0.12,
      verdict: "winner_treatment",
      sample_size_control: 500,
      sample_size_treatment: 500,
    },
  ],
  result: {
    winner: "treatment",
    p_value: 0.003,
    effect_size: 0.12,
    confidence_interval: [0.04, 0.20],
    concluded_at: "2026-04-01T10:05:00",
    reason: "Treatment significantly outperformed control",
  },
};

// ---------------------------------------------------------------------------
// Report fixtures
// ---------------------------------------------------------------------------

export const mockReportSummaries: ReportSummary[] = [
  {
    report_id: "report-playbook-001",
    type: "playbook_health",
    title: "Playbook Health Report",
    summary: "3 active learnings, 1 stale",
    generated_at: "2026-04-03T14:00:00",
    campaign_ids: [],
  },
  {
    report_id: "report-perf-001",
    type: "campaign_performance",
    title: "Spring Sale Performance",
    summary: "v2 outperformed v1 on open_rate",
    generated_at: "2026-04-03T15:00:00",
    campaign_ids: ["spring-sale"],
  },
];

export const mockReportDetail: ReportDetail = {
  report_id: "report-perf-001",
  type: "campaign_performance",
  title: "Spring Sale Performance",
  summary: "v2 outperformed v1 on open_rate",
  generated_at: "2026-04-03T15:00:00",
  campaign_ids: ["spring-sale"],
  sections: [
    { heading: "Overview", content: "Campaign ran for 3 days." },
    { heading: "Results", content: "v2 had 41% higher open rate than v1." },
  ],
};

// ---------------------------------------------------------------------------
// Transfer fixtures
// ---------------------------------------------------------------------------

export const mockTransferProposed = {
  transfer_id: "transfer-abc123",
  source_channel: "email",
  target_channel: "sms",
  hypothesis: "Playful tone from email will also improve SMS click-through",
  status: "proposed",
  learning_text: "Playful tone increases engagement by 15%",
  created_at: "2026-04-02T10:00:00",
};

export const mockTransferConfirmed = {
  transfer_id: "transfer-def456",
  source_channel: "email",
  target_channel: "ad",
  hypothesis: "Urgency CTA from email works in ad copy",
  status: "confirmed",
  learning_text: "Urgency CTAs boost conversion by 20%",
  created_at: "2026-04-01T08:00:00",
  result: "confirmed",
};
