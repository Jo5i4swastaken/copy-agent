'use client';

interface ToolActivityProps {
  toolName: string | null;
  args?: Record<string, unknown>;
}

export default function ToolActivity({ toolName, args }: ToolActivityProps) {
  if (!toolName) return null;

  return (
    <div
      className="
        flex items-center gap-2 px-4 py-2
        animate-fade-in
        transition-opacity duration-normal
      "
      role="status"
      aria-live="polite"
      aria-label={`Running tool: ${toolName}`}
    >
      {/* Spinning indicator */}
      <svg
        className="w-3.5 h-3.5 text-accent animate-spin shrink-0"
        viewBox="0 0 16 16"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="8"
          cy="8"
          r="6.5"
          stroke="currentColor"
          strokeOpacity="0.25"
          strokeWidth="2.5"
        />
        <path
          d="M14.5 8a6.5 6.5 0 0 0-6.5-6.5"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>

      <span className="text-xs text-accent font-medium truncate">
        Running: <span className="font-mono">{toolName}</span>...
      </span>

      {args && Object.keys(args).length > 0 && (
        <span className="text-xs text-muted truncate hidden sm:inline">
          ({Object.keys(args).join(', ')})
        </span>
      )}
    </div>
  );
}
