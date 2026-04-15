"use client";

import React from "react";

// ---------------------------------------------------------------------------
// TestStateTimeline — Horizontal stepper showing A/B test progression
// ---------------------------------------------------------------------------

const STATES = [
  "DESIGNED",
  "DEPLOYING",
  "COLLECTING",
  "DECIDED",
  "COMPLETED",
] as const;

type TestState = (typeof STATES)[number];

const STATE_LABELS: Record<TestState, string> = {
  DESIGNED: "Designed",
  DEPLOYING: "Deploying",
  COLLECTING: "Collecting",
  DECIDED: "Decided",
  COMPLETED: "Completed",
};

interface TestStateTimelineProps {
  currentState: string;
  createdAt: string;
  timestamps?: Record<string, string>;
}

function getStateIndex(state: string): number {
  const upper = state.toUpperCase() as TestState;
  const idx = STATES.indexOf(upper);
  return idx >= 0 ? idx : -1;
}

/**
 * Horizontal stepper component visualizing the A/B test lifecycle.
 * Completed steps are highlighted in accent color, the current step
 * pulses, and future steps are muted.
 */
export function TestStateTimeline({
  currentState,
  createdAt,
  timestamps = {},
}: TestStateTimelineProps) {
  const activeIdx = getStateIndex(currentState);

  return (
    <div className="w-full" role="list" aria-label="Test state timeline">
      <div className="flex items-start justify-between relative">
        {/* Connecting line behind the steps */}
        <div className="absolute top-4 left-0 right-0 h-0.5 bg-border-subtle" />
        <div
          className="absolute top-4 left-0 h-0.5 bg-accent transition-all duration-slow"
          style={{
            width:
              activeIdx >= 0
                ? `${(activeIdx / (STATES.length - 1)) * 100}%`
                : "0%",
          }}
        />

        {STATES.map((state, idx) => {
          const isComplete = idx < activeIdx;
          const isCurrent = idx === activeIdx;
          const isFuture = idx > activeIdx;

          const timestamp =
            idx === 0
              ? createdAt
              : timestamps[state] ?? timestamps[state.toLowerCase()] ?? null;

          return (
            <div
              key={state}
              className="relative flex flex-col items-center z-10"
              style={{ flex: 1 }}
              role="listitem"
              aria-current={isCurrent ? "step" : undefined}
            >
              {/* Step circle */}
              <div
                className={`
                  w-8 h-8 rounded-full flex items-center justify-center
                  border-2 transition-all duration-normal
                  ${
                    isComplete
                      ? "bg-accent border-accent"
                      : isCurrent
                        ? "bg-accent/20 border-accent animate-agent-pulse"
                        : "bg-surface border-border-subtle"
                  }
                `}
              >
                {isComplete ? (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 14 14"
                    fill="none"
                    aria-hidden="true"
                  >
                    <path
                      d="M11 4L5.5 9.5 3 7"
                      stroke="hsl(var(--accent-foreground))"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                ) : (
                  <span
                    className={`text-xs font-semibold ${
                      isCurrent ? "text-accent" : "text-muted"
                    }`}
                  >
                    {idx + 1}
                  </span>
                )}
              </div>

              {/* Label */}
              <span
                className={`mt-2 text-xs font-medium text-center ${
                  isComplete
                    ? "text-foreground"
                    : isCurrent
                      ? "text-accent"
                      : "text-muted"
                }`}
              >
                {STATE_LABELS[state]}
              </span>

              {/* Timestamp */}
              {timestamp && (
                <span className="mt-0.5 text-xs text-muted tabular-nums">
                  {formatTimestamp(timestamp)}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatTimestamp(iso: string): string {
  try {
    const date = new Date(iso);
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
