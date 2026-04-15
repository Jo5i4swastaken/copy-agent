import { NextResponse } from "next/server";
import { readdir, readFile } from "fs/promises";
import path from "path";

// ---------------------------------------------------------------------------
// Path resolution
// ---------------------------------------------------------------------------

function getDataDir(): string {
  if (process.env.COPY_AGENT_DATA_DIR) {
    return path.resolve(process.env.COPY_AGENT_DATA_DIR);
  }
  return path.resolve(__dirname, "..", "..", "..", "..", "data");
}

async function readJsonFile<T>(filePath: string): Promise<T | null> {
  try {
    const raw = await readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// GET /api/reports/[reportId] — fetch a single report
// ---------------------------------------------------------------------------

/**
 * Returns the full content of a single report by its ID.
 * Searches data/reports/ for a matching JSON file.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ reportId: string }> },
) {
  try {
    const { reportId } = await params;
    const dataDir = getDataDir();
    const reportsDir = path.join(dataDir, "reports");

    // Try direct file match first: {reportId}.json
    const directPath = path.join(reportsDir, `${reportId}.json`);
    const directData = await readJsonFile<Record<string, unknown>>(directPath);

    if (directData) {
      return NextResponse.json(directData);
    }

    // Fall back to scanning all files for a matching report_id
    let fileNames: string[] = [];
    try {
      const entries = await readdir(reportsDir);
      fileNames = entries.filter((f) => f.endsWith(".json"));
    } catch {
      return NextResponse.json(
        { error: "Report not found" },
        { status: 404 },
      );
    }

    for (const fileName of fileNames) {
      const filePath = path.join(reportsDir, fileName);
      const data = await readJsonFile<Record<string, unknown>>(filePath);
      if (data && (data.report_id === reportId || data.id === reportId)) {
        return NextResponse.json(data);
      }
    }

    return NextResponse.json(
      { error: `Report "${reportId}" not found` },
      { status: 404 },
    );
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to load report";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
