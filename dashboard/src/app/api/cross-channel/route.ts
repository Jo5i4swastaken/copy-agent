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
// Transfer interface
// ---------------------------------------------------------------------------

interface TransferHypothesis {
  transfer_id: string;
  source_channel: string;
  target_channel: string;
  source_learning_id: string;
  hypothesis: string;
  status: "proposed" | "testing" | "confirmed" | "rejected";
  linked_test_id: string | null;
  created_at: string;
  updated_at: string;
  confidence: number;
  evidence: string;
}

// ---------------------------------------------------------------------------
// GET /api/cross-channel — list all transfer hypotheses
// ---------------------------------------------------------------------------

/**
 * Reads transfer JSON files from data/orchestration/transfers/ and returns
 * them sorted by creation date (newest first).
 */
export async function GET() {
  try {
    const dataDir = getDataDir();
    const transfersDir = path.join(dataDir, "orchestration", "transfers");

    let fileNames: string[] = [];
    try {
      const entries = await readdir(transfersDir);
      fileNames = entries.filter((f) => f.endsWith(".json"));
    } catch {
      // transfers/ may not exist yet — return empty array
      return NextResponse.json([]);
    }

    const transfers: TransferHypothesis[] = [];

    const results = await Promise.all(
      fileNames.map(async (fileName) => {
        const filePath = path.join(transfersDir, fileName);
        return readJsonFile<TransferHypothesis>(filePath);
      }),
    );

    for (const data of results) {
      if (data && data.transfer_id) {
        transfers.push(data);
      }
    }

    // Sort newest first
    transfers.sort((a, b) => {
      if (a.created_at > b.created_at) return -1;
      if (a.created_at < b.created_at) return 1;
      return 0;
    });

    return NextResponse.json(transfers);
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Failed to list cross-channel transfers";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
