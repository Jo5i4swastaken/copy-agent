'use client';

// =============================================================================
// useAgentWebSocket.ts — React hook for OmniAgents WebSocket connection
//
// Manages the full lifecycle of the WebSocket connection to the OmniAgents
// server: connecting, sending prompts, handling streamed events, tool approval,
// auto-reconnect, and cleanup on unmount.
// =============================================================================

import { useState, useRef, useCallback, useEffect } from 'react';
import type { ChatMessage } from '@/lib/types';
import {
  getWebSocketUrl,
  createStartRun,
  createGetAgentInfo,
  createToolApproval,
  parseAgentMessage,
} from '@/lib/agent-rpc';

// ---------------------------------------------------------------------------
// Public interface
// ---------------------------------------------------------------------------

export interface UseAgentWebSocket {
  /** Whether the WebSocket is currently connected. */
  isConnected: boolean;
  /** True between run_started and run_end events. */
  isRunning: boolean;
  /** Chat history (user, assistant, and system messages). */
  messages: ChatMessage[];
  /** The tool currently being executed, or null. */
  toolActivity: { name: string; args: Record<string, unknown> } | null;

  /** Send a user prompt — adds a user message and starts a run. */
  sendMessage: (
    prompt: string,
    files: File[],
    options: { thinking: boolean },
  ) => void;
  /** Respond to a tool approval request. */
  approveToolCall: (
    requestId: string,
    approved: boolean,
    alwaysApprove?: boolean,
  ) => void;
  /** Clear the chat history. */
  clearMessages: () => void;
  /** Open (or re-open) the WebSocket connection. */
  connect: () => void;
  /** Close the WebSocket connection. */
  disconnect: () => void;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY_MS = 3_000;

const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Generate a simple unique ID for chat messages. */
function uid(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function readFileAsDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(reader.error ?? new Error('FileReader error'));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== 'string') {
        reject(new Error('Unexpected FileReader result'));
        return;
      }
      resolve(result);
    };
    reader.readAsDataURL(file);
  });
}

// ---------------------------------------------------------------------------
// Hook implementation
// ---------------------------------------------------------------------------

export function useAgentWebSocket(): UseAgentWebSocket {
  // -- State ----------------------------------------------------------------
  const [isConnected, setIsConnected] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [toolActivity, setToolActivity] = useState<{
    name: string;
    args: Record<string, unknown>;
  } | null>(null);

  // -- Refs (stable across renders, no re-render on mutation) ---------------
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const intentionalCloseRef = useRef(false);
  const isConnectedRef = useRef(false);
  const currentRunIdRef = useRef<string | null>(null);

  // We track the "last assistant message id" in a ref so the message_output
  // handler can accumulate streamed content into a single message without
  // depending on stale state closures.
  const lastAssistantIdRef = useRef<string | null>(null);

  // -------------------------------------------------------------------------
  // WebSocket message handler
  // -------------------------------------------------------------------------

  const handleMessage = useCallback((event: MessageEvent) => {
    const parsed = parseAgentMessage(event.data as string);

    // We only act on events from the agent; responses to our RPC calls
    // (e.g. get_agent_info) are silently acknowledged.
    if (parsed.kind !== 'event') return;

    const agentEvent = parsed.event;

    switch (agentEvent.type) {
      // -- Run lifecycle ----------------------------------------------------
      case 'run_started': {
        currentRunIdRef.current = agentEvent.run_id;
        setIsRunning(true);
        break;
      }

      case 'run_end': {
        currentRunIdRef.current = null;
        lastAssistantIdRef.current = null;
        setIsRunning(false);
        setToolActivity(null);
        break;
      }

      // -- Streamed assistant text ------------------------------------------
      case 'message_output': {
        const content = agentEvent.content ?? '';
        const lastId = lastAssistantIdRef.current;

        setMessages((prev) => {
          // If the most recent message is from the assistant (same id), append.
          if (lastId) {
            const idx = prev.findIndex((m) => m.id === lastId);
            if (idx !== -1 && prev[idx].role === 'assistant') {
              const updated = [...prev];
              updated[idx] = {
                ...updated[idx],
                content: updated[idx].content + content,
                timestamp: agentEvent.timestamp,
              };
              return updated;
            }
          }

          // Otherwise create a new assistant message.
          const newId = uid();
          lastAssistantIdRef.current = newId;
          return [
            ...prev,
            {
              id: newId,
              role: 'assistant' as const,
              content,
              timestamp: agentEvent.timestamp,
              run_id: agentEvent.run_id,
            },
          ];
        });
        break;
      }

      // -- Tool execution ---------------------------------------------------
      case 'tool_called': {
        setToolActivity({
          name: agentEvent.tool_name,
          args: agentEvent.arguments,
        });

        setMessages((prev) => [
          ...prev,
          {
            id: uid(),
            role: 'system' as const,
            content: `Calling tool: ${agentEvent.tool_name}`,
            timestamp: agentEvent.timestamp,
            run_id: agentEvent.run_id,
            tool_activity: [
              {
                tool_name: agentEvent.tool_name,
                arguments: agentEvent.arguments,
                status: 'calling' as const,
              },
            ],
          },
        ]);

        // Reset the assistant accumulation — next text output should start a
        // fresh message after the tool activity.
        lastAssistantIdRef.current = null;
        break;
      }

      case 'tool_result': {
        setToolActivity(null);

        // Update the most recent system message for this tool to "complete".
        setMessages((prev) => {
          const idx = [...prev]
            .reverse()
            .findIndex(
              (m) =>
                m.role === 'system' &&
                m.tool_activity?.[0]?.tool_name === agentEvent.tool_name &&
                m.tool_activity?.[0]?.status === 'calling',
            );
          if (idx === -1) return prev;
          const realIdx = prev.length - 1 - idx;
          const updated = [...prev];
          updated[realIdx] = {
            ...updated[realIdx],
            tool_activity: [
              {
                ...updated[realIdx].tool_activity![0],
                result: agentEvent.result,
                status: 'complete' as const,
              },
            ],
          };
          return updated;
        });
        break;
      }

      // -- Tool approval request --------------------------------------------
      case 'client_request': {
        setMessages((prev) => [
          ...prev,
          {
            id: `approval-${agentEvent.request_id}`,
            role: 'system' as const,
            content: agentEvent.message || `Approve tool: ${agentEvent.tool_name}?`,
            timestamp: agentEvent.timestamp,
            run_id: agentEvent.run_id,
            tool_activity: [
              {
                tool_name: agentEvent.tool_name,
                arguments: agentEvent.arguments,
                status: 'calling' as const,
              },
            ],
          },
        ]);

        // Reset assistant accumulation so post-approval text is a new message.
        lastAssistantIdRef.current = null;
        break;
      }
    }
  }, []);

  // -------------------------------------------------------------------------
  // Connection management
  // -------------------------------------------------------------------------

  const connect = useCallback(() => {
    // Prevent duplicate connections.
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.OPEN ||
        wsRef.current.readyState === WebSocket.CONNECTING)
    ) {
      return;
    }

    intentionalCloseRef.current = false;
    const url = getWebSocketUrl();

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      isConnectedRef.current = true;
      reconnectAttemptsRef.current = 0;

      // Send get_agent_info to verify the connection.
      ws.send(createGetAgentInfo());
    };

    ws.onmessage = handleMessage;

    ws.onerror = (err) => {
      console.error('[useAgentWebSocket] WebSocket error:', err);
    };

    ws.onclose = () => {
      const wasConnected = isConnectedRef.current;
      setIsConnected(false);
      isConnectedRef.current = false;
      wsRef.current = null;

      // Only auto-reconnect if we had a successful connection before
      // (not on initial connection failures to a server that's not running).
      if (
        !intentionalCloseRef.current &&
        wasConnected &&
        reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS
      ) {
        reconnectAttemptsRef.current += 1;
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, RECONNECT_DELAY_MS);
      }
    };
  }, [handleMessage]);

  const disconnect = useCallback(() => {
    intentionalCloseRef.current = true;

    // Clear any pending reconnect timer.
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsRunning(false);
    setToolActivity(null);
  }, []);

  // -------------------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------------------

  const sendMessage: UseAgentWebSocket['sendMessage'] = useCallback(
    (prompt: string, files: File[], options: { thinking: boolean }) => {
      void (async () => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          console.warn(
            '[useAgentWebSocket] Cannot send message — WebSocket is not connected.',
          );
          return;
        }

        const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
        if (totalBytes > MAX_ATTACHMENT_BYTES) {
          console.warn(
            `[useAgentWebSocket] Attachments too large (${totalBytes} bytes) — refusing to send.`,
          );
          setMessages((prev) => [
            ...prev,
            {
              id: uid(),
              role: 'system' as const,
              content:
                'Attachments are too large (25MB limit). Please remove some files and try again.',
              timestamp: new Date().toISOString(),
            },
          ]);
          return;
        }

        const attachments = await Promise.all(
          files.map(async (file) => {
            const dataUrl = await readFileAsDataUrl(file);
            const commaIdx = dataUrl.indexOf(',');
            const data_base64 = commaIdx >= 0 ? dataUrl.slice(commaIdx + 1) : '';
            return {
              name: file.name,
              mime: file.type || 'application/octet-stream',
              data_base64,
            };
          }),
        );

        const totalBase64Bytes = attachments.reduce((sum, att) => {
          const padding = att.data_base64.endsWith('==')
            ? 2
            : att.data_base64.endsWith('=')
              ? 1
              : 0;
          const bytes = Math.floor((att.data_base64.length * 3) / 4) - padding;
          return sum + Math.max(bytes, 0);
        }, 0);
        if (totalBase64Bytes > MAX_ATTACHMENT_BYTES) {
          console.warn(
            `[useAgentWebSocket] Base64 payload too large (${totalBase64Bytes} bytes) — refusing to send.`,
          );
          setMessages((prev) => [
            ...prev,
            {
              id: uid(),
              role: 'system' as const,
              content:
                'Attachments are too large after encoding (25MB limit). Please remove some files and try again.',
              timestamp: new Date().toISOString(),
            },
          ]);
          return;
        }

        // Add user message to the chat (metadata only; do not retain base64).
        const userMessage: ChatMessage = {
          id: uid(),
          role: 'user',
          content: prompt,
          timestamp: new Date().toISOString(),
          ...(attachments.length
            ? {
                attachments: attachments.map(({ name, mime }) => ({ name, mime })),
              }
            : {}),
        };
        setMessages((prev) => [...prev, userMessage]);

        // Reset assistant accumulation for the new run.
        lastAssistantIdRef.current = null;

        // We send files via OmniAgents' native `attachments` start_run param.
        wsRef.current.send(
          createStartRun(prompt, {
            thinking: options.thinking,
            ...(attachments.length ? { attachments } : {}),
          }),
        );
      })();
    },
    [],
  );

  const approveToolCall = useCallback(
    (requestId: string, approved: boolean, alwaysApprove: boolean = false) => {
      if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        console.warn(
          '[useAgentWebSocket] Cannot send approval — WebSocket is not connected.',
        );
        return;
      }

      // Send the approval response.
      wsRef.current.send(createToolApproval(requestId, approved, alwaysApprove));

      // Update the corresponding approval message in chat.
      const approvalMsgId = `approval-${requestId}`;
      const statusLabel = approved ? 'Approved' : 'Denied';

      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== approvalMsgId) return msg;
          return {
            ...msg,
            content: `${msg.content} — ${statusLabel}`,
            tool_activity: msg.tool_activity?.map((ta) => ({
              ...ta,
              status: approved ? ('complete' as const) : ('error' as const),
            })),
          };
        }),
      );
    },
    [],
  );

  const clearMessages = useCallback(() => {
    setMessages([]);
    lastAssistantIdRef.current = null;
  }, []);

  // -------------------------------------------------------------------------
  // Lifecycle — connect on mount, cleanup on unmount
  // -------------------------------------------------------------------------

  useEffect(() => {
    connect();

    return () => {
      intentionalCloseRef.current = true;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
    // `connect` is stable (useCallback with stable deps), safe to include.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // -------------------------------------------------------------------------
  // Return
  // -------------------------------------------------------------------------

  return {
    isConnected,
    isRunning,
    messages,
    toolActivity,
    sendMessage,
    approveToolCall,
    clearMessages,
    connect,
    disconnect,
  };
}
