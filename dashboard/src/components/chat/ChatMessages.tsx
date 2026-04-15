'use client';

import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import type { ChatMessage } from '@/lib/types';
import ToolApproval from './ToolApproval';

interface ChatMessagesProps {
  messages: ChatMessage[];
  isRunning: boolean;
  onApproveToolCall?: (requestId: string, approved: boolean) => void;
}

/**
 * Formats a timestamp into a human-readable time string.
 */
function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

/**
 * Thinking indicator with three animated dots.
 * Uses the .thinking-dot-1/2/3 classes from globals.css
 * paired with the thinking-dot animation from tailwind.config.ts.
 */
function ThinkingIndicator() {
  return (
    <div className="flex justify-start px-4 py-2" aria-label="Agent is thinking" role="status">
      <div className="flex items-center gap-1.5 bg-surface rounded-2xl rounded-tl-md px-4 py-3">
        <div
          className="w-2 h-2 rounded-full bg-accent animate-thinking-dot thinking-dot-1"
          aria-hidden="true"
        />
        <div
          className="w-2 h-2 rounded-full bg-accent animate-thinking-dot thinking-dot-2"
          aria-hidden="true"
        />
        <div
          className="w-2 h-2 rounded-full bg-accent animate-thinking-dot thinking-dot-3"
          aria-hidden="true"
        />
        <span className="sr-only">Copy Agent is thinking...</span>
      </div>
    </div>
  );
}

/**
 * Empty state shown when there are no messages.
 */
function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 text-center">
      <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center mb-4">
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          className="text-accent"
          aria-hidden="true"
        >
          <path
            d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
      <p className="text-muted text-sm">Start a conversation with Copy Agent...</p>
    </div>
  );
}

/**
 * Renders a single user message bubble (right-aligned, accent background).
 */
function UserMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end px-4 py-1.5">
      <div className="max-w-[85%] flex flex-col items-end gap-1">
        <div className="bg-accent text-accent-foreground rounded-2xl rounded-tr-md px-4 py-2.5">
          <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <span className="text-[10px] text-muted px-1">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  );
}

/**
 * Renders a single assistant message bubble (left-aligned, surface background)
 * with markdown rendering for content.
 */
function AssistantMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-start px-4 py-1.5">
      <div className="max-w-[85%] flex flex-col items-start gap-1">
        <div className="bg-surface rounded-2xl rounded-tl-md px-4 py-2.5">
          <div className="text-sm text-foreground prose-chat">
            <ReactMarkdown
              components={{
                p: ({ children }) => (
                  <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>
                ),
                strong: ({ children }) => (
                  <strong className="font-semibold text-foreground">{children}</strong>
                ),
                em: ({ children }) => (
                  <em className="text-foreground-secondary">{children}</em>
                ),
                code: ({ children }) => (
                  <code className="bg-elevated px-1.5 py-0.5 rounded text-xs font-mono text-accent">
                    {children}
                  </code>
                ),
                pre: ({ children }) => (
                  <pre className="bg-elevated rounded-badge p-3 overflow-x-auto text-xs my-2">
                    {children}
                  </pre>
                ),
                ul: ({ children }) => (
                  <ul className="list-disc list-inside mb-2 space-y-1">{children}</ul>
                ),
                ol: ({ children }) => (
                  <ol className="list-decimal list-inside mb-2 space-y-1">{children}</ol>
                ),
                li: ({ children }) => (
                  <li className="text-sm leading-relaxed">{children}</li>
                ),
                a: ({ href, children }) => (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent underline underline-offset-2 hover:text-accent/80"
                  >
                    {children}
                  </a>
                ),
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        </div>
        <span className="text-[10px] text-muted px-1">{formatTime(message.timestamp)}</span>
      </div>
    </div>
  );
}

/**
 * Renders a system message (centered, muted, smaller font).
 */
function SystemMessage({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-center px-4 py-1">
      <div className="max-w-[90%] text-center">
        <p className="text-xs text-muted leading-relaxed">{message.content}</p>
      </div>
    </div>
  );
}

/**
 * Renders a tool approval request inline in the chat timeline.
 * Extracts tool_name, args, and request_id from the message content or tool_activity.
 */
function ToolApprovalMessage({ message, onApprove }: { message: ChatMessage; onApprove?: (requestId: string, approved: boolean) => void }) {
  // Parse the tool approval data from the first tool_activity entry
  const activity = message.tool_activity?.[0];

  if (!activity) {
    return <SystemMessage message={message} />;
  }

  return (
    <div className="flex justify-start px-4 py-1.5">
      <ToolApproval
        toolName={activity.tool_name}
        args={activity.arguments}
        requestId={message.id}
        onApprove={(requestId: string, approved: boolean) => {
          onApprove?.(requestId, approved);
        }}
        status={
          activity.status === 'complete'
            ? 'approved'
            : activity.status === 'error'
              ? 'denied'
              : 'pending'
        }
      />
    </div>
  );
}

export default function ChatMessages({ messages, isRunning, onApproveToolCall }: ChatMessagesProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomAnchorRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when messages change or when agent starts running
  useEffect(() => {
    const anchor = bottomAnchorRef.current;
    if (anchor) {
      anchor.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isRunning]);

  // Empty state
  if (messages.length === 0 && !isRunning) {
    return (
      <div className="chat-messages" ref={scrollContainerRef}>
        <EmptyState />
      </div>
    );
  }

  // Determine if thinking indicator should show:
  // Agent is running AND the last message is not from the assistant
  const showThinking =
    isRunning && (messages.length === 0 || messages[messages.length - 1].role !== 'assistant');

  return (
    <div
      className="chat-messages"
      ref={scrollContainerRef}
      role="log"
      aria-label="Chat messages"
      aria-live="polite"
    >
      <div className="py-4 flex flex-col gap-0.5">
        {messages.map((message) => {
          // Check if this is a tool_approval message by inspecting tool_activity
          const isToolApproval =
            message.tool_activity &&
            message.tool_activity.length > 0 &&
            message.role === 'system';

          if (isToolApproval) {
            return <ToolApprovalMessage key={message.id} message={message} onApprove={onApproveToolCall} />;
          }

          switch (message.role) {
            case 'user':
              return <UserMessage key={message.id} message={message} />;
            case 'assistant':
              return <AssistantMessage key={message.id} message={message} />;
            case 'system':
              return <SystemMessage key={message.id} message={message} />;
            default:
              return null;
          }
        })}

        {showThinking && <ThinkingIndicator />}

        {/* Invisible anchor for auto-scroll */}
        <div ref={bottomAnchorRef} aria-hidden="true" />
      </div>
    </div>
  );
}
