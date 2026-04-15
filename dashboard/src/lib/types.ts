// =============================================================================
// types.ts — TypeScript types for the Copy Agent dashboard
//
// Derived from the actual JSON schemas written by the Python tools:
//   - tools/copy_tools.py    (Brief, Variant, Campaign)
//   - tools/metrics_tools.py (MetricEntry, MetricType)
//   - tools/analysis_tools.py (AnalysisResult, PlaybookEntry, Playbook)
//   - data/playbook.json     (Playbook seed data)
//
// Plus OmniAgents JSON-RPC 2.0 WebSocket protocol types.
// =============================================================================

// ---------------------------------------------------------------------------
// Copy channels
// ---------------------------------------------------------------------------

/** Valid marketing channels supported by the Copy Agent. */
export type Channel = "email" | "sms" | "seo" | "ad";

/** Campaign and variant status values. */
export type CampaignStatus = "draft" | "active" | "complete";

// ---------------------------------------------------------------------------
// Brief — written by generate_copy to brief.json
// ---------------------------------------------------------------------------

/**
 * A campaign brief as persisted in `data/campaigns/{id}/brief.json`.
 * See `copy_tools.py` lines 113-121.
 */
export interface Brief {
  campaign_id: string;
  campaign_name: string;
  brief: string;
  channel: Channel;
  num_variants: number;
  created_at: string; // ISO 8601 datetime
  status: CampaignStatus;
}

// ---------------------------------------------------------------------------
// Variant — written by save_copy_variant to variants.json
// ---------------------------------------------------------------------------

/**
 * A single copy variant as persisted in `data/campaigns/{id}/variants.json`.
 * See `copy_tools.py` lines 211-221.
 */
export interface Variant {
  variant_id: string;
  channel: Channel;
  content: string;
  subject_line: string; // primarily for email; empty string for other channels
  cta: string;
  tone: string;
  notes: string;
  created_at: string; // ISO 8601 datetime
  status: CampaignStatus;
}

// ---------------------------------------------------------------------------
// MetricEntry — written by log_metrics to metrics.json
// ---------------------------------------------------------------------------

/**
 * Valid metric type identifiers accepted by `metrics_tools.py`.
 * See `VALID_METRIC_TYPES` in metrics_tools.py lines 17-33.
 */
export type MetricType =
  | "open_rate"
  | "click_rate"
  | "reply_rate"
  | "conversion_rate"
  | "unsubscribe_rate"
  | "impressions"
  | "clicks"
  | "ctr"
  | "cost_per_click"
  | "roas"
  | "bounce_rate"
  | "time_on_page"
  | "search_position"
  | "delivery_rate"
  | "opt_out_rate";

/**
 * A single metric data point as persisted in `data/campaigns/{id}/metrics.json`.
 * See `metrics_tools.py` lines 113-119.
 */
export interface MetricEntry {
  variant_id: string;
  metric_type: MetricType;
  value: number;
  date: string;        // YYYY-MM-DD
  notes: string;
  logged_at: string;   // ISO 8601 datetime
}

// ---------------------------------------------------------------------------
// Campaign — composite type for a fully loaded campaign
// ---------------------------------------------------------------------------

/**
 * Summary used in campaign list views (no variant/metric bodies).
 */
export interface CampaignSummary {
  campaign_id: string;
  campaign_name: string;
  channel: Channel;
  status: CampaignStatus;
  created_at: string;
  num_variants: number;
}

/**
 * Full campaign with brief, variants, and optional metrics.
 * Assembled by reading brief.json, variants.json, and metrics.json together.
 */
export interface Campaign {
  brief: Brief;
  variants: Variant[];
  metrics: MetricEntry[];
}

// ---------------------------------------------------------------------------
// Playbook — data/playbook.json
// ---------------------------------------------------------------------------

/** Category values used by the playbook. */
export type PlaybookCategory = "email" | "sms" | "seo" | "ad" | "general";

/** Source indicator for a playbook entry. */
export type PlaybookSource = "seed" | "data-driven" | string;

/**
 * A single learning entry in the playbook.
 * See `data/playbook.json` and `analysis_tools.py` lines 595-606.
 */
export interface PlaybookEntry {
  id: string;                    // e.g. "seed_001" or "learn_001"
  category: PlaybookCategory;
  learning: string;
  evidence: string;
  confidence: number;            // 0.3 = low, 0.6 = medium, 0.9 = high
  times_confirmed: number;
  times_contradicted: number;
  first_observed: string;        // YYYY-MM-DD
  last_confirmed: string;        // YYYY-MM-DD
  tags: string[];
  source?: PlaybookSource;       // present on seed entries, absent on data-driven
}

/**
 * The top-level playbook structure as persisted in `data/playbook.json`.
 */
export interface Playbook {
  version: number;
  last_updated: string;          // ISO 8601 datetime
  learnings: PlaybookEntry[];
}

// ---------------------------------------------------------------------------
// Analysis result — output shape from analyze_campaign
// ---------------------------------------------------------------------------

/**
 * Winner info for a single metric, produced by the analysis tool.
 * See `analysis_tools.py` lines 237-244.
 */
export interface MetricWinner {
  winner_id: string;
  winner_val: number;
  loser_id: string;
  loser_val: number;
  pct_diff: string;              // e.g. "23.5%"
  direction: "higher is better" | "lower is better";
}

/**
 * Structured analysis result. The Python tool returns a formatted string,
 * but the dashboard can reconstruct this from raw data for richer rendering.
 */
export interface AnalysisResult {
  campaign_id: string;
  campaign_name: string;
  channel: Channel;
  variants_analyzed: number;
  metrics_tracked: string[];
  variant_averages: Record<string, Record<string, number>>;   // variant_id -> metric_type -> avg value
  winners: Record<string, MetricWinner>;                      // metric_type -> winner info
  overall_winner: string | null;
  overall_win_count: number;
  total_metrics_compared: number;
  differences: string[];
  suggested_learnings: string[];
}

// ---------------------------------------------------------------------------
// Aggregated metrics — for dashboard chart views
// ---------------------------------------------------------------------------

/**
 * Metrics aggregated across campaigns for dashboard-level visualization.
 */
export interface AggregatedMetrics {
  /** Total campaigns in the data directory. */
  total_campaigns: number;

  /** Breakdown of campaigns by channel. */
  campaigns_by_channel: Record<Channel, number>;

  /** Breakdown of campaigns by status. */
  campaigns_by_status: Record<string, number>;

  /** Total variants across all campaigns. */
  total_variants: number;

  /** Total metric data points across all campaigns. */
  total_metric_entries: number;

  /**
   * Per-metric-type averages across all campaigns.
   * Useful for showing benchmark/trend lines.
   */
  metric_averages: Partial<Record<MetricType, number>>;

  /**
   * Time series of metric values for charting.
   * Each entry represents a data point with its campaign context.
   */
  metric_timeline: MetricTimelineEntry[];
}

/**
 * A single point in the metric timeline, enriched with campaign context.
 */
export interface MetricTimelineEntry {
  campaign_id: string;
  campaign_name: string;
  channel: Channel;
  variant_id: string;
  metric_type: MetricType;
  value: number;
  date: string;
}

// =============================================================================
// JSON-RPC 2.0 protocol types — OmniAgents WebSocket server
// =============================================================================

// ---------------------------------------------------------------------------
// Base JSON-RPC types
// ---------------------------------------------------------------------------

/** JSON-RPC 2.0 request (expects a response). */
export interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: string | number;
  method: string;
  params?: Record<string, unknown>;
}

/** JSON-RPC 2.0 notification (no response expected). */
export interface JsonRpcNotification {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown>;
}

/** JSON-RPC 2.0 success response. */
export interface JsonRpcSuccessResponse {
  jsonrpc: "2.0";
  id: string | number;
  result: unknown;
}

/** JSON-RPC 2.0 error response. */
export interface JsonRpcErrorResponse {
  jsonrpc: "2.0";
  id: string | number;
  error: {
    code: number;
    message: string;
    data?: unknown;
  };
}

/** Union of both response shapes. */
export type JsonRpcResponse = JsonRpcSuccessResponse | JsonRpcErrorResponse;

// ---------------------------------------------------------------------------
// Agent event types — notifications from server to client
// ---------------------------------------------------------------------------

/** Emitted when a new agent run begins. */
export interface RunStartedEvent {
  type: "run_started";
  run_id: string;
  timestamp: string;
}

/** Emitted when the agent calls a tool. */
export interface ToolCalledEvent {
  type: "tool_called";
  run_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  timestamp: string;
}

/** Emitted when a tool returns its result. */
export interface ToolResultEvent {
  type: "tool_result";
  run_id: string;
  tool_name: string;
  result: string;
  timestamp: string;
}

/**
 * Emitted when the agent needs client approval (e.g. to run a tool).
 * The dashboard must respond with a client_response message.
 */
export interface ClientRequestEvent {
  type: "client_request";
  request_id: string;
  run_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  message: string;
  timestamp: string;
}

/** Emitted when the agent produces a text message. */
export interface MessageOutputEvent {
  type: "message_output";
  run_id: string;
  content: string;
  timestamp: string;
}

/** Emitted when the agent run completes. */
export interface RunEndEvent {
  type: "run_end";
  run_id: string;
  timestamp: string;
}

/** Discriminated union of all possible agent events. */
export type AgentEvent =
  | RunStartedEvent
  | ToolCalledEvent
  | ToolResultEvent
  | ClientRequestEvent
  | MessageOutputEvent
  | RunEndEvent;

/** String literal union matching AgentEvent["type"]. */
export type AgentEventType = AgentEvent["type"];

// ---------------------------------------------------------------------------
// Tool approval request/response — for client_request handling
// ---------------------------------------------------------------------------

/**
 * Represents a pending tool approval the UI must show to the user.
 * Built from a ClientRequestEvent.
 */
export interface ToolApprovalRequest {
  request_id: string;
  run_id: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  message: string;
  timestamp: string;
}

/**
 * The user's response to a tool approval request.
 */
export interface ToolApprovalResponse {
  request_id: string;
  approved: boolean;
  always_approve: boolean;
}

// ---------------------------------------------------------------------------
// Chat message — UI-level representation for the chat panel
// ---------------------------------------------------------------------------

/** Role in a chat message. */
export type ChatRole = "user" | "assistant" | "system";

/** Activity state for tool calls shown inline in chat. */
export type ToolActivity = {
  tool_name: string;
  arguments: Record<string, unknown>;
  result?: string;
  status: "calling" | "complete" | "error";
};

/**
 * A single message in the chat panel UI.
 * Combines agent text output, user input, and tool activity into a
 * unified timeline.
 */
export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;           // ISO 8601 datetime
  tool_activity?: ToolActivity[];
  run_id?: string;
}

// ---------------------------------------------------------------------------
// Agent info — returned by get_agent_info
// ---------------------------------------------------------------------------

/**
 * Agent metadata returned by the `get_agent_info` RPC method.
 */
export interface AgentInfo {
  name: string;
  description: string;
  tools: AgentToolInfo[];
}

/**
 * Metadata for a single tool exposed by the agent.
 */
export interface AgentToolInfo {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
}
