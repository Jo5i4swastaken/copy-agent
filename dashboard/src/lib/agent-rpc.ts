// =============================================================================
// agent-rpc.ts — JSON-RPC 2.0 message builders for OmniAgents WebSocket
//
// Provides typed constructors for outbound messages and a parser for
// inbound notifications.  Designed for use in React hooks or plain
// WebSocket handlers.
//
// OmniAgents server protocol reference:
//   Outbound methods:
//     start_run       { prompt: string }
//     get_agent_info  {}
//     client_response { request_id, ok, result: { approved, always_approve } }
//
//   Inbound notifications:
//     run_started, tool_called, tool_result, client_request,
//     message_output, run_end
// =============================================================================

import type {
  JsonRpcRequest,
  JsonRpcResponse,
  AgentEvent,
  AgentEventType,
  RunStartedEvent,
  ToolCalledEvent,
  ToolResultEvent,
  ClientRequestEvent,
  MessageOutputEvent,
  RunEndEvent,
} from "./types";

// ---------------------------------------------------------------------------
// ID generation — monotonically increasing per session
// ---------------------------------------------------------------------------

let _nextId = 1;

/** Return a unique numeric request id for the current browser session. */
function nextId(): number {
  return _nextId++;
}

/**
 * Reset the request ID counter. Useful in tests or when reconnecting.
 */
export function resetIdCounter(): void {
  _nextId = 1;
}

// ---------------------------------------------------------------------------
// Outbound message constructors
// ---------------------------------------------------------------------------

/**
 * Build a `start_run` JSON-RPC request that sends the user's prompt to the
 * agent and begins a new run.
 *
 * @param prompt - The user's message / instruction for the agent.
 * @returns A serialized JSON string ready to send over the WebSocket.
 */
export function createStartRun(prompt: string): string {
  const request: JsonRpcRequest = {
    jsonrpc: "2.0",
    id: nextId(),
    method: "start_run",
    params: { prompt },
  };
  return JSON.stringify(request);
}

/**
 * Build a `get_agent_info` JSON-RPC request to retrieve agent metadata
 * (name, description, available tools).
 *
 * @returns A serialized JSON string ready to send over the WebSocket.
 */
export function createGetAgentInfo(): string {
  const request: JsonRpcRequest = {
    jsonrpc: "2.0",
    id: nextId(),
    method: "get_agent_info",
    params: {},
  };
  return JSON.stringify(request);
}

/**
 * Build a `client_response` JSON-RPC request that answers a tool approval
 * prompt from the agent.
 *
 * This is sent in reply to a `client_request` notification.  The server
 * uses `request_id` to correlate the response with the original request.
 *
 * @param requestId     - The `request_id` from the ClientRequestEvent.
 * @param approved      - Whether the user approved the tool execution.
 * @param alwaysApprove - If true, the server should auto-approve future
 *                        calls to the same tool for this run.
 * @returns A serialized JSON string ready to send over the WebSocket.
 */
export function createToolApproval(
  requestId: string,
  approved: boolean,
  alwaysApprove: boolean = false,
): string {
  const request: JsonRpcRequest = {
    jsonrpc: "2.0",
    id: nextId(),
    method: "client_response",
    params: {
      request_id: requestId,
      ok: true,
      result: {
        approved,
        always_approve: alwaysApprove,
      },
    },
  };
  return JSON.stringify(request);
}

// ---------------------------------------------------------------------------
// Inbound message parser
// ---------------------------------------------------------------------------

/** All event types the parser recognises. */
const KNOWN_EVENT_TYPES: Set<AgentEventType> = new Set([
  "run_started",
  "tool_called",
  "tool_result",
  "client_request",
  "message_output",
  "run_end",
]);

/**
 * Discriminator result returned by `parseAgentMessage`.
 *
 * - `{ kind: "event", event }` for server notifications
 * - `{ kind: "response", response }` for RPC responses (to our requests)
 * - `{ kind: "unknown", raw }` for anything we cannot classify
 */
export type ParsedMessage =
  | { kind: "event"; event: AgentEvent }
  | { kind: "response"; response: JsonRpcResponse }
  | { kind: "unknown"; raw: unknown };

/**
 * Parse a raw WebSocket message string into a typed structure.
 *
 * The OmniAgents server sends two categories of messages:
 *   1. **Notifications** — have a `method` field matching one of the known
 *      event types. The `params` object contains the event payload.
 *   2. **Responses** — have an `id` field matching one of our prior requests,
 *      plus either a `result` or `error` field.
 *
 * @param message - The raw string received from `WebSocket.onmessage`.
 * @returns A discriminated union wrapping the parsed result.
 */
export function parseAgentMessage(message: string): ParsedMessage {
  let parsed: Record<string, unknown>;

  try {
    parsed = JSON.parse(message) as Record<string, unknown>;
  } catch {
    return { kind: "unknown", raw: message };
  }

  // -------------------------------------------------------------------
  // Check for a notification (has `method`, no `id`)
  // -------------------------------------------------------------------
  const method = parsed.method as string | undefined;

  if (method && KNOWN_EVENT_TYPES.has(method as AgentEventType)) {
    const params = (parsed.params ?? {}) as Record<string, unknown>;
    const timestamp =
      (params.timestamp as string) ?? new Date().toISOString();

    const getToolName = (): string => {
      const toolName = params.tool_name ?? params.tool;
      return typeof toolName === "string" && toolName.length > 0
        ? toolName
        : "<tool>";
    };

    const getToolArguments = (): Record<string, unknown> => {
      const raw =
        (params.arguments as unknown) ??
        (params.input as unknown) ??
        (params.args as unknown);

      if (raw == null) return {};

      if (typeof raw === "object" && !Array.isArray(raw)) {
        return raw as Record<string, unknown>;
      }

      if (typeof raw === "string") {
        const trimmed = raw.trim();
        if (!trimmed) return {};
        try {
          const parsedJson = JSON.parse(trimmed) as unknown;
          if (
            parsedJson &&
            typeof parsedJson === "object" &&
            !Array.isArray(parsedJson)
          ) {
            return parsedJson as Record<string, unknown>;
          }
          return { input: parsedJson };
        } catch {
          return { input: trimmed };
        }
      }

      return { input: raw };
    };

    const getToolResult = (): string => {
      const raw = (params.result as unknown) ?? (params.output as unknown);
      if (raw == null) return "";
      return typeof raw === "string" ? raw : JSON.stringify(raw);
    };

    switch (method as AgentEventType) {
      case "run_started": {
        const event: RunStartedEvent = {
          type: "run_started",
          run_id: params.run_id as string,
          timestamp,
        };
        return { kind: "event", event };
      }

      case "tool_called": {
        const event: ToolCalledEvent = {
          type: "tool_called",
          run_id: params.run_id as string,
          tool_name: getToolName(),
          arguments: getToolArguments(),
          timestamp,
        };
        return { kind: "event", event };
      }

      case "tool_result": {
        const event: ToolResultEvent = {
          type: "tool_result",
          run_id: params.run_id as string,
          tool_name: getToolName(),
          result: getToolResult(),
          timestamp,
        };
        return { kind: "event", event };
      }

      case "client_request": {
        const event: ClientRequestEvent = {
          type: "client_request",
          request_id: params.request_id as string,
          run_id: params.run_id as string,
          tool_name: getToolName(),
          arguments: getToolArguments(),
          message: params.message as string,
          timestamp,
        };
        return { kind: "event", event };
      }

      case "message_output": {
        const event: MessageOutputEvent = {
          type: "message_output",
          run_id: params.run_id as string,
          content: params.content as string,
          timestamp,
        };
        return { kind: "event", event };
      }

      case "run_end": {
        const event: RunEndEvent = {
          type: "run_end",
          run_id: params.run_id as string,
          timestamp,
        };
        return { kind: "event", event };
      }
    }
  }

  // -------------------------------------------------------------------
  // Check for a JSON-RPC response (has `id` + `result` or `error`)
  // -------------------------------------------------------------------
  if ("id" in parsed && ("result" in parsed || "error" in parsed)) {
    return {
      kind: "response",
      response: parsed as unknown as JsonRpcResponse,
    };
  }

  // -------------------------------------------------------------------
  // Unrecognised
  // -------------------------------------------------------------------
  return { kind: "unknown", raw: parsed };
}

/**
 * Convenience wrapper that only extracts AgentEvent objects, discarding
 * responses and unknown messages. Returns `null` for non-event messages.
 *
 * Useful in simple chat panel implementations that only care about the
 * event stream.
 *
 * @param message - The raw WebSocket message string.
 * @returns The parsed AgentEvent, or null.
 */
export function parseAgentEvent(message: string): AgentEvent | null {
  const result = parseAgentMessage(message);
  if (result.kind === "event") {
    return result.event;
  }
  return null;
}

// ---------------------------------------------------------------------------
// WebSocket URL helper
// ---------------------------------------------------------------------------

/** Default OmniAgents server WebSocket URL. */
export const DEFAULT_WS_URL = "ws://localhost:9494/ws";

/**
 * Build the WebSocket URL, allowing override via environment variable
 * or explicit parameter.
 *
 * Priority: explicit url > NEXT_PUBLIC_AGENT_WS_URL env var > default.
 */
export function getWebSocketUrl(url?: string): string {
  if (url) return url;
  if (typeof process !== "undefined" && process.env?.NEXT_PUBLIC_AGENT_WS_URL) {
    return process.env.NEXT_PUBLIC_AGENT_WS_URL;
  }
  return DEFAULT_WS_URL;
}
