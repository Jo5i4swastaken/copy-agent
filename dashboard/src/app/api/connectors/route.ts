import { NextResponse } from "next/server";
import { readFile, writeFile } from "fs/promises";
import path from "path";

/**
 * Resolve the agent's .env file path.
 */
function getEnvPath(): string {
  return path.resolve(__dirname, "..", "..", "..", "..", "..", ".env");
}

/**
 * GET /api/connectors
 *
 * Returns which platform integrations are configured based on
 * environment variables.
 */
export async function GET() {
  try {
    const status: Record<
      string,
      { configured: boolean; detail: string }
    > = {
      sendgrid: {
        configured: !!process.env.SENDGRID_API_KEY,
        detail: process.env.SENDGRID_API_KEY
          ? "API key configured"
          : "SENDGRID_API_KEY not set",
      },
      twilio: {
        configured: !!(
          process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN
        ),
        detail:
          process.env.TWILIO_ACCOUNT_SID && process.env.TWILIO_AUTH_TOKEN
            ? "Credentials configured"
            : "TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN not set",
      },
      google_search_console: {
        configured: !!process.env.GOOGLE_SERVICE_ACCOUNT_JSON,
        detail: process.env.GOOGLE_SERVICE_ACCOUNT_JSON
          ? "Service account configured"
          : "GOOGLE_SERVICE_ACCOUNT_JSON not set",
      },
      google_ads: {
        configured: !!(
          process.env.GOOGLE_SERVICE_ACCOUNT_JSON &&
          process.env.GOOGLE_ADS_CUSTOMER_ID
        ),
        detail:
          process.env.GOOGLE_SERVICE_ACCOUNT_JSON &&
          process.env.GOOGLE_ADS_CUSTOMER_ID
            ? "Credentials configured"
            : "GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_ADS_CUSTOMER_ID not set",
      },
    };

    return NextResponse.json(status);
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "Failed to check connector status";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

/**
 * POST /api/connectors
 *
 * Accepts key-value pairs and writes them to the agent's .env file.
 * Also updates process.env so the change takes effect without restart
 * for the dashboard's own status checks.
 *
 * Body: { envVars: Record<string, string> }
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const envVars: Record<string, string> = body.envVars;

    if (!envVars || typeof envVars !== "object") {
      return NextResponse.json(
        { error: "envVars object is required" },
        { status: 400 },
      );
    }

    // Read the existing .env file
    const envPath = getEnvPath();
    let envContent = "";
    try {
      envContent = await readFile(envPath, "utf-8");
    } catch {
      // File doesn't exist yet — we'll create it
    }

    // Parse existing lines into a map
    const lines = envContent.split("\n");
    const existingKeys = new Set<string>();
    const updatedLines: string[] = [];

    for (const line of lines) {
      const trimmed = line.trim();
      // Check if this line sets a key we're updating
      const match = trimmed.match(/^([A-Z_][A-Z0-9_]*)=/);
      if (match && match[1] in envVars) {
        // Replace with new value
        updatedLines.push(`${match[1]}=${envVars[match[1]]}`);
        existingKeys.add(match[1]);
      } else {
        updatedLines.push(line);
      }
    }

    // Append any new keys that weren't already in the file
    for (const [key, value] of Object.entries(envVars)) {
      if (!existingKeys.has(key) && value) {
        updatedLines.push(`${key}=${value}`);
      }
    }

    // Write back
    await writeFile(envPath, updatedLines.join("\n"), "utf-8");

    // Update process.env in-memory so GET reflects the change immediately
    for (const [key, value] of Object.entries(envVars)) {
      if (value) {
        process.env[key] = value;
      }
    }

    return NextResponse.json({
      success: true,
      message:
        "Credentials saved to .env. Restart the agent server to activate the integration.",
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to save credentials";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
