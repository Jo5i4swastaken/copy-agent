import { NextResponse } from "next/server";
import { getAggregatedMetrics } from "@/lib/data-reader";

/**
 * GET /api/metrics
 *
 * Returns an AggregatedMetrics object with totals, per-channel breakdowns,
 * metric averages, and a chronological timeline for charting.
 *
 * This endpoint powers the dashboard overview charts and KPI cards.
 */
export async function GET() {
  try {
    const metrics = await getAggregatedMetrics();
    return NextResponse.json(metrics);
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Failed to load aggregated metrics";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
