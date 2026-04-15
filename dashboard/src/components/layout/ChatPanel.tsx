"use client";

import { useAgentWebSocket } from "@/hooks/useAgentWebSocket";
import ChatMessages from "@/components/chat/ChatMessages";
import ChatInput from "@/components/chat/ChatInput";
import ToolActivity from "@/components/chat/ToolActivity";

interface ChatPanelProps {
  isOpen: boolean;
  onToggle: () => void;
}

export function ChatPanel({ isOpen, onToggle }: ChatPanelProps) {
  const {
    isConnected,
    isRunning,
    messages,
    toolActivity,
    sendMessage,
    approveToolCall,
  } = useAgentWebSocket();

  return (
    <>
      {/* Chat Panel */}
      <div
        className="chat-panel bg-surface border-l border-border shadow-panel"
        data-open={isOpen}
        role="complementary"
        aria-label="Chat panel"
      >
        {/* Header */}
        <div className="chat-panel-header border-b border-border-subtle">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-accent/10">
              <svg
                width="14"
                height="14"
                viewBox="0 0 14 14"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M7 1L1.5 4v6L7 13l5.5-3V4L7 1z"
                  stroke="hsl(var(--accent))"
                  strokeWidth="1.2"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
            <h2 className="font-display text-sm font-semibold text-foreground">
              Copy Agent
            </h2>
            {/* Connection indicator */}
            <span
              className={`ml-1 inline-block h-2 w-2 rounded-full ${
                isConnected ? "bg-success" : "bg-error"
              }`}
              title={isConnected ? "Connected" : "Disconnected"}
            />
          </div>
          <button
            type="button"
            onClick={onToggle}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted transition-colors hover:bg-elevated hover:text-foreground"
            aria-label="Close chat panel"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              aria-hidden="true"
            >
              <line x1="4" y1="4" x2="12" y2="12" />
              <line x1="12" y1="4" x2="4" y2="12" />
            </svg>
          </button>
        </div>

        {/* Messages */}
        <ChatMessages
          messages={messages}
          isRunning={isRunning}
          onApproveToolCall={approveToolCall}
        />

        {/* Tool activity indicator */}
        <ToolActivity
          toolName={toolActivity?.name ?? null}
          args={toolActivity?.args}
        />

        {/* Input */}
        <ChatInput onSend={sendMessage} disabled={!isConnected} />
      </div>

      {/* Floating Action Button — visible when panel is closed */}
      <button
        type="button"
        className="chat-fab bg-accent text-accent-foreground"
        data-hidden={isOpen}
        onClick={onToggle}
        aria-label="Open chat panel"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
        </svg>
      </button>
    </>
  );
}
