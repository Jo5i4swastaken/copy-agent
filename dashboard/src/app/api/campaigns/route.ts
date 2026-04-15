import { NextResponse } from "next/server";
import { listCampaigns } from "@/lib/data-reader";
import type { Channel } from "@/lib/types";

/**
 * GET /api/campaigns
 *
 * Returns a JSON array of CampaignSummary objects.
 *
 * Optional query parameters:
 *   - channel: Filter by marketing channel (email | sms | seo | ad)
 *   - status:  Filter by campaign status (draft | active | complete)
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);

    const channel = searchParams.get("channel") as Channel | null;
    const status = searchParams.get("status");

    const filters: { channel?: Channel; status?: string } = {};
    if (channel) filters.channel = channel;
    if (status) filters.status = status;

    const campaigns = await listCampaigns(
      Object.keys(filters).length > 0 ? filters : undefined,
    );

    return NextResponse.json(campaigns);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to list campaigns";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
