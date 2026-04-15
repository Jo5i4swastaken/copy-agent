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
// Report summary interface
// ---------------------------------------------------------------------------

interface ReportSummary {
  report_id: string;
  type: string;
  title: string;
  summary: string;
  generated_at: string;
  campaign_ids: string[];
}

// ---------------------------------------------------------------------------
// GET /api/reports — list all generated reports
// ---------------------------------------------------------------------------

/**
 * Reads report files from data/reports/ and returns summaries
 * sorted by generation date (newest first).
 */
export async function GET() {
  try {
    const dataDir = getDataDir();
    const reportsDir = path.join(dataDir, "reports");

    let fileNames: string[] = [];
    try {
      const entries = await readdir(reportsDir);
      fileNames = entries.filter((f) => f.endsWith(".json"));
    } catch {
      // reports/ may not exist yet
      return NextResponse.json([]);
    }

    const reports: ReportSummary[] = [];

    const results = await Promise.all(
      fileNames.map(async (fileName) => {
        const filePath = path.join(reportsDir, fileName);
        return readJsonFile<Record<string, unknown>>(filePath);
      }),
    );

    for (const data of results) {
      if (!data) continue;

      reports.push({
        report_id:
          (data.report_id as string) ??
          (data.id as string) ??
          "",
        type: (data.type as string) ?? "general",
        title: (data.title as string) ?? "Untitled Report",
        summary: (data.summary as string) ?? "",
        generated_at: (data.generated_at as string) ?? (data.created_at as string) ?? "",
        campaign_ids: Array.isArray(data.campaign_ids)
          ? (data.campaign_ids as string[])
          : [],
      });
    }

    // Sort newest first
    reports.sort((a, b) => {
      if (a.generated_at > b.generated_at) return -1;
      if (a.generated_at < b.generated_at) return 1;
      return 0;
    });

    return NextResponse.json(reports);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to list reports";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
