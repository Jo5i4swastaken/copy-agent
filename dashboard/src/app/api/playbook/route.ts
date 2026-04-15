import { NextResponse } from "next/server";
import { getPlaybook, getPlaybookByCategory } from "@/lib/data-reader";

/**
 * GET /api/playbook
 *
 * Returns the full Playbook object. When the optional `category` query
 * parameter is provided, the learnings array is filtered to only include
 * entries matching that category (sorted by confidence, highest first).
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const category = searchParams.get("category");

    if (category) {
      const filteredLearnings = await getPlaybookByCategory(category);
      const playbook = await getPlaybook();

      return NextResponse.json({
        version: playbook.version,
        last_updated: playbook.last_updated,
        learnings: filteredLearnings,
      });
    }

    const playbook = await getPlaybook();
    return NextResponse.json(playbook);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to load playbook";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
