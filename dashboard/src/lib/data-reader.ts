// =============================================================================
// data-reader.ts — Server-side data access for Next.js API routes
//
// Reads the JSON files produced by the Copy Agent's Python tools.
// This module uses Node.js `fs/promises` and must only be imported in
// server-side code (API routes, `getServerSideProps`, Server Components).
//
// All reads are defensive: missing files return sensible defaults instead
// of throwing, because new campaigns may not yet have variants or metrics.
// =============================================================================

import { readdir, readFile } from "fs/promises";
import path from "path";

import type {
  Brief,
  Campaign,
  CampaignSummary,
  Channel,
  MetricEntry,
  MetricType,
  MetricTimelineEntry,
  Playbook,
  PlaybookEntry,
  Variant,
  AggregatedMetrics,
} from "./types";

// ---------------------------------------------------------------------------
// Path resolution
// ---------------------------------------------------------------------------

/**
 * Resolve the absolute path to the agent's `data/` directory.
 *
 * The dashboard lives at `<project-root>/dashboard/`, so `data/` is one
 * level up: `<project-root>/data/`.
 *
 * Supports override via the `COPY_AGENT_DATA_DIR` environment variable
 * for deployment flexibility.
 */
export function getDataDir(): string {
  if (process.env.COPY_AGENT_DATA_DIR) {
    return path.resolve(process.env.COPY_AGENT_DATA_DIR);
  }
  // dashboard/src/lib/data-reader.ts -> dashboard/ -> project root -> data/
  return path.resolve(__dirname, "..", "..", "..", "..", "data");
}

/**
 * Resolve the absolute path to the campaigns directory.
 */
function getCampaignsDir(): string {
  return path.join(getDataDir(), "campaigns");
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Read and parse a JSON file. Returns `null` if the file does not exist
 * or cannot be parsed (graceful degradation for incomplete campaign data).
 */
async function readJsonFile<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    // File missing, permission error, or malformed JSON — all handled
    return null;
  }
}

/**
 * List subdirectory names inside a directory. Returns an empty array
 * if the directory does not exist.
 */
async function listSubdirectories(dirPath: string): Promise<string[]> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true });
    return entries.filter((e) => e.isDirectory()).map((e) => e.name);
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * List all campaigns with summary metadata, sorted by creation date
 * (newest first).
 *
 * Reads only `brief.json` per campaign plus a quick variant count from
 * `variants.json`. Skips campaigns with missing or corrupt briefs.
 *
 * @param filters - Optional channel and status filters.
 * @returns Array of CampaignSummary objects.
 */
export async function listCampaigns(filters?: {
  channel?: Channel;
  status?: string;
}): Promise<CampaignSummary[]> {
  const campaignsDir = getCampaignsDir();
  const dirNames = await listSubdirectories(campaignsDir);

  const summaries: CampaignSummary[] = [];

  // Read all briefs in parallel for speed
  const briefResults = await Promise.all(
    dirNames.map(async (dirName) => {
      const briefPath = path.join(campaignsDir, dirName, "brief.json");
      const brief = await readJsonFile<Brief>(briefPath);
      return { dirName, brief };
    }),
  );

  for (const { dirName, brief } of briefResults) {
    if (!brief) continue;

    // Apply optional filters
    if (filters?.channel && brief.channel !== filters.channel) continue;
    if (filters?.status && brief.status !== filters.status) continue;

    // Count variants without loading full content
    let numVariants = 0;
    const variantsPath = path.join(campaignsDir, dirName, "variants.json");
    const variants = await readJsonFile<Variant[]>(variantsPath);
    if (Array.isArray(variants)) {
      numVariants = variants.length;
    }

    summaries.push({
      campaign_id: brief.campaign_id ?? dirName,
      campaign_name: brief.campaign_name ?? "",
      channel: brief.channel,
      status: brief.status,
      created_at: brief.created_at,
      num_variants: numVariants,
    });
  }

  // Sort newest first
  summaries.sort((a, b) => {
    if (a.created_at > b.created_at) return -1;
    if (a.created_at < b.created_at) return 1;
    return 0;
  });

  return summaries;
}

/**
 * Load the full data for a single campaign: brief, variants, and metrics.
 *
 * Variants and metrics default to empty arrays when their files do not
 * exist yet (common for newly created campaigns).
 *
 * @param id - The campaign_id (directory name under `data/campaigns/`).
 * @returns The Campaign object, or `null` if the brief is missing.
 */
export async function getCampaign(id: string): Promise<Campaign | null> {
  const campaignDir = path.join(getCampaignsDir(), id);

  const brief = await readJsonFile<Brief>(
    path.join(campaignDir, "brief.json"),
  );

  if (!brief) {
    return null; // Campaign does not exist
  }

  const [variants, metrics] = await Promise.all([
    readJsonFile<Variant[]>(path.join(campaignDir, "variants.json")),
    readJsonFile<MetricEntry[]>(path.join(campaignDir, "metrics.json")),
  ]);

  return {
    brief,
    variants: Array.isArray(variants) ? variants : [],
    metrics: Array.isArray(metrics) ? metrics : [],
  };
}

/**
 * Read the marketing playbook.
 *
 * Returns a Playbook with an empty learnings array if the file does
 * not exist yet.
 */
export async function getPlaybook(): Promise<Playbook> {
  const playbookPath = path.join(getDataDir(), "playbook.json");
  const data = await readJsonFile<Playbook>(playbookPath);

  if (!data) {
    return {
      version: 0,
      last_updated: "",
      learnings: [],
    };
  }

  return data;
}

/**
 * Aggregate metrics across all campaigns for dashboard-level charts
 * and KPI cards.
 *
 * Scans every campaign directory, loading briefs, variants, and metrics
 * in parallel for efficiency. Produces:
 *   - Total/channel/status counts
 *   - Per-metric-type averages across all campaigns
 *   - A chronological timeline suitable for line/area charts
 */
export async function getAggregatedMetrics(): Promise<AggregatedMetrics> {
  const campaignsDir = getCampaignsDir();
  const dirNames = await listSubdirectories(campaignsDir);

  // Accumulators
  const campaignsByChannel: Record<string, number> = {};
  const campaignsByStatus: Record<string, number> = {};
  let totalVariants = 0;
  let totalMetricEntries = 0;

  // Per-metric-type accumulators for averaging
  const metricSums: Partial<Record<MetricType, number>> = {};
  const metricCounts: Partial<Record<MetricType, number>> = {};

  // Timeline entries
  const timeline: MetricTimelineEntry[] = [];

  // Load all campaign data in parallel
  const campaignDataResults = await Promise.all(
    dirNames.map(async (dirName) => {
      const dir = path.join(campaignsDir, dirName);
      const [brief, variants, metrics] = await Promise.all([
        readJsonFile<Brief>(path.join(dir, "brief.json")),
        readJsonFile<Variant[]>(path.join(dir, "variants.json")),
        readJsonFile<MetricEntry[]>(path.join(dir, "metrics.json")),
      ]);
      return { dirName, brief, variants, metrics };
    }),
  );

  for (const { dirName, brief, variants, metrics } of campaignDataResults) {
    if (!brief) continue;

    // Channel and status tallies
    const ch = brief.channel ?? "unknown";
    campaignsByChannel[ch] = (campaignsByChannel[ch] ?? 0) + 1;

    const st = brief.status ?? "unknown";
    campaignsByStatus[st] = (campaignsByStatus[st] ?? 0) + 1;

    // Variant count
    const variantList = Array.isArray(variants) ? variants : [];
    totalVariants += variantList.length;

    // Metric entries
    const metricList = Array.isArray(metrics) ? metrics : [];
    totalMetricEntries += metricList.length;

    for (const entry of metricList) {
      const mt = entry.metric_type;

      // Running sums for averages
      metricSums[mt] = (metricSums[mt] ?? 0) + entry.value;
      metricCounts[mt] = (metricCounts[mt] ?? 0) + 1;

      // Timeline entry
      timeline.push({
        campaign_id: brief.campaign_id ?? dirName,
        campaign_name: brief.campaign_name ?? dirName,
        channel: brief.channel,
        variant_id: entry.variant_id,
        metric_type: mt,
        value: entry.value,
        date: entry.date,
      });
    }
  }

  // Compute averages
  const metricAverages: Partial<Record<MetricType, number>> = {};
  for (const mt of Object.keys(metricSums) as MetricType[]) {
    const sum = metricSums[mt] ?? 0;
    const count = metricCounts[mt] ?? 1;
    metricAverages[mt] = sum / count;
  }

  // Sort timeline chronologically
  timeline.sort((a, b) => {
    if (a.date < b.date) return -1;
    if (a.date > b.date) return 1;
    return 0;
  });

  return {
    total_campaigns: campaignDataResults.filter((r) => r.brief !== null).length,
    campaigns_by_channel: campaignsByChannel as Record<Channel, number>,
    campaigns_by_status: campaignsByStatus,
    total_variants: totalVariants,
    total_metric_entries: totalMetricEntries,
    metric_averages: metricAverages,
    metric_timeline: timeline,
  };
}

// ---------------------------------------------------------------------------
// Utility: get playbook entries filtered by category
// ---------------------------------------------------------------------------

/**
 * Convenience function to retrieve playbook learnings for a specific
 * category, sorted by confidence (highest first).
 *
 * @param category - The playbook category to filter by.
 * @returns Sorted array of PlaybookEntry objects.
 */
export async function getPlaybookByCategory(
  category: string,
): Promise<PlaybookEntry[]> {
  const playbook = await getPlaybook();
  return playbook.learnings
    .filter((entry) => entry.category === category)
    .sort((a, b) => b.confidence - a.confidence);
}

// ---------------------------------------------------------------------------
// Utility: get latest metrics for a campaign (latest per variant+metric)
// ---------------------------------------------------------------------------

/**
 * For a given campaign, return only the most recent metric entry per
 * (variant_id, metric_type) pair. Useful for summary cards that show
 * current performance without historical noise.
 *
 * @param id - The campaign_id.
 * @returns Map of `variant_id -> metric_type -> MetricEntry`.
 */
export async function getLatestMetrics(
  id: string,
): Promise<Record<string, Record<string, MetricEntry>>> {
  const campaign = await getCampaign(id);
  if (!campaign) return {};

  const latest: Record<string, Record<string, MetricEntry>> = {};

  for (const entry of campaign.metrics) {
    const vid = entry.variant_id;
    const mt = entry.metric_type;

    if (!latest[vid]) {
      latest[vid] = {};
    }

    const existing = latest[vid][mt];
    if (!existing || entry.logged_at > existing.logged_at) {
      latest[vid][mt] = entry;
    }
  }

  return latest;
}
