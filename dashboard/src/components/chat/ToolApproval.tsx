'use client';

import { useState, useCallback } from 'react';

interface ToolApprovalProps {
  toolName: string;
  args: Record<string, unknown>;
  requestId: string;
  onApprove: (requestId: string, approved: boolean) => void;
  status?: 'pending' | 'approved' | 'denied';
}

/**
 * Truncates a string value to a maximum length, adding ellipsis if needed.
 */
function truncateValue(value: unknown, maxLength = 80): string {
  let str: string;

  if (typeof value === 'string') {
    str = value;
  } else if (
    value === null ||
    typeof value === 'number' ||
    typeof value === 'boolean' ||
    typeof value === 'bigint'
  ) {
    str = String(value);
  } else if (Array.isArray(value)) {
    str = `[Array(${value.length})]`;
  } else if (typeof value === 'object') {
    const keys = Object.keys(value as Record<string, unknown>);
    const shown = keys.slice(0, 6).join(', ');
    str = keys.length <= 6 ? `{${shown}}` : `{${shown}, ...}`;
  } else {
    str = String(value);
  }

  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength) + '...';
}

/**
 * Renders a compact JSON preview of tool arguments.
 */
function ArgsPreview({ args }: { args: Record<string, unknown> }) {
  const entries = Object.entries(args);

  if (entries.length === 0) {
    return (
      <span className="text-muted text-xs italic">No arguments</span>
    );
  }

  return (
    <div className="space-y-1">
      {entries.map(([key, value]) => (
        <div key={key} className="flex gap-2 text-xs leading-relaxed">
          <span className="text-accent font-mono shrink-0">{key}:</span>
          <span className="text-foreground-secondary font-mono break-all">
            {truncateValue(value)}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function ToolApproval({
  toolName,
  args,
  requestId,
  onApprove,
  status = 'pending',
}: ToolApprovalProps) {
  const [localStatus, setLocalStatus] = useState<'pending' | 'approved' | 'denied'>(status);

  const handleApprove = useCallback(() => {
    setLocalStatus('approved');
    onApprove(requestId, true);
  }, [requestId, onApprove]);

  const handleDeny = useCallback(() => {
    setLocalStatus('denied');
    onApprove(requestId, false);
  }, [requestId, onApprove]);

  const isPending = localStatus === 'pending';

  return (
    <div
      className={`
        rounded-card border bg-elevated/60 p-3 max-w-[320px]
        transition-all duration-normal
        ${isPending ? 'animate-pulse border-accent/40' : 'border-border'}
      `}
      role="alert"
      aria-label={`Tool approval request for ${toolName}`}
    >
      {/* Tool name header */}
      <div className="flex items-center gap-2 mb-2">
        <div className="w-2 h-2 rounded-full bg-warning shrink-0" aria-hidden="true" />
        <span className="font-mono text-sm font-medium text-foreground">
          {toolName}
        </span>
      </div>

      {/* Arguments preview */}
      <div className="bg-background/60 rounded-badge p-2 mb-3 border border-border-subtle">
        <ArgsPreview args={args} />
      </div>

      {/* Action buttons or status badge */}
      {isPending ? (
        <div className="flex gap-2">
          <button
            onClick={handleApprove}
            className="
              flex-1 px-3 py-1.5 rounded-badge text-xs font-medium
              bg-success/15 text-success border border-success/30
              hover:bg-success/25 transition-colors duration-fast
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-success
            "
            aria-label={`Approve ${toolName}`}
          >
            Approve
          </button>
          <button
            onClick={handleDeny}
            className="
              flex-1 px-3 py-1.5 rounded-badge text-xs font-medium
              bg-error/15 text-error border border-error/30
              hover:bg-error/25 transition-colors duration-fast
              focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-error
            "
            aria-label={`Deny ${toolName}`}
          >
            Deny
          </button>
        </div>
      ) : (
        <div
          className={`
            inline-flex items-center gap-1.5 px-2.5 py-1 rounded-badge text-xs font-medium
            ${localStatus === 'approved'
              ? 'bg-success/15 text-success'
              : 'bg-error/15 text-error'
            }
          `}
          role="status"
        >
          <div
            className={`w-1.5 h-1.5 rounded-full ${
              localStatus === 'approved' ? 'bg-success' : 'bg-error'
            }`}
            aria-hidden="true"
          />
          {localStatus === 'approved' ? 'Approved' : 'Denied'}
        </div>
      )}
    </div>
  );
}
