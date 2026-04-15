import { NextResponse } from "next/server";
import { getCampaign } from "@/lib/data-reader";

/**
 * GET /api/campaigns/:id
 *
 * Returns the full Campaign object (brief + variants + metrics) for a
 * single campaign. Returns 404 when the campaign does not exist.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const campaign = await getCampaign(id);

    if (!campaign) {
      return NextResponse.json(
        { error: `Campaign "${id}" not found` },
        { status: 404 },
      );
    }

    return NextResponse.json(campaign);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to load campaign";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
