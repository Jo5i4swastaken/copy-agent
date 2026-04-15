import { NextResponse } from "next/server";
import { readdir, readFile } from "fs/promises";
import path from "path";

// ---------------------------------------------------------------------------
// Path resolution — mirrors data-reader.ts pattern
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

async function listSubdirectories(dirPath: string): Promise<string[]> {
  try {
    const entries = await readdir(dirPath, { withFileTypes: true });
    return entries.filter((e) => e.isDirectory()).map((e) => e.name);
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// A/B Test State interface (mirrors Python ab_test_tools output)
// ---------------------------------------------------------------------------

interface ABTestState {
  test_id: string;
  campaign_id: string;
  state: string;
  hypothesis: string;
  control_variant_id: string;
  treatment_variant_id: string;
  metric_type: string;
  created_at: string;
  next_check_at: string | null;
  max_duration_hours: number;
  checks: ABTestCheck[];
  result: ABTestResult | null;
}

interface ABTestCheck {
  check_number: number;
  checked_at: string;
  control_value: number;
  treatment_value: number;
  p_value: number | null;
  effect_size: number | null;
  verdict: string;
  sample_size_control: number;
  sample_size_treatment: number;
}

interface ABTestResult {
  winner: string | null;
  p_value: number | null;
  effect_size: number | null;
  confidence_interval: [number, number] | null;
  concluded_at: string;
  reason: string;
}

// ---------------------------------------------------------------------------
// GET /api/ab-tests — list all A/B tests
// ---------------------------------------------------------------------------

/**
 * Scans campaign directories for ab_test_state.json files and returns
 * all A/B tests sorted by creation date (newest first).
 *
 * Also checks data/orchestration/ab-tests/ for standalone test state files.
 */
export async function GET() {
  try {
    const dataDir = getDataDir();
    const tests: ABTestState[] = [];

    // Strategy 1: Scan campaign dirs for ab_test_state.json
    const campaignsDir = path.join(dataDir, "campaigns");
    const campaignDirs = await listSubdirectories(campaignsDir);

    const campaignResults = await Promise.all(
      campaignDirs.map(async (dirName) => {
        const statePath = path.join(
          campaignsDir,
          dirName,
          "ab_test_state.json",
        );
        return readJsonFile<ABTestState>(statePath);
      }),
    );

    for (const state of campaignResults) {
      if (state && state.test_id) {
        tests.push(state);
      }
    }

    // Strategy 2: Scan data/orchestration/ab-tests/ for test files
    const orchestrationDir = path.join(dataDir, "orchestration", "ab-tests");
    try {
      const entries = await readdir(orchestrationDir);
      const jsonFiles = entries.filter((f) => f.endsWith(".json"));

      const orchestrationResults = await Promise.all(
        jsonFiles.map(async (fileName) => {
          const filePath = path.join(orchestrationDir, fileName);
          return readJsonFile<ABTestState>(filePath);
        }),
      );

      for (const state of orchestrationResults) {
        if (state && state.test_id) {
          // Deduplicate by test_id
          const exists = tests.some((t) => t.test_id === state.test_id);
          if (!exists) {
            tests.push(state);
          }
        }
      }
    } catch {
      // orchestration/ab-tests/ may not exist yet — that is fine
    }

    // Sort newest first
    tests.sort((a, b) => {
      if (a.created_at > b.created_at) return -1;
      if (a.created_at < b.created_at) return 1;
      return 0;
    });

    return NextResponse.json(tests);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to list A/B tests";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
