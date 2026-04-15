"use client";

import { useABTests } from "@/hooks/useABTests";
import Link from "next/link";

const STATE_COLORS: Record<string, string> = {
  COLLECTING: "bg-blue-500/10 text-blue-400",
  WAITING: "bg-yellow-500/10 text-yellow-400",
  ANALYZING: "bg-purple-500/10 text-purple-400",
  DECIDED: "bg-success/10 text-success",
  COMPLETED: "bg-foreground-secondary/10 text-foreground-secondary",
  INCONCLUSIVE: "bg-error/10 text-error",
  DESIGNED: "bg-elevated text-muted",
  DEPLOYING: "bg-yellow-500/10 text-yellow-400",
};

function SkeletonCard() {
  return (
    <div className="rounded-card border border-border bg-surface p-5 shadow-card" aria-hidden="true">
      <div className="mb-3 flex items-center justify-between">
        <div className="skeleton h-5 w-24 rounded-badge" />
        <div className="skeleton h-5 w-16 rounded-badge" />
      </div>
      <div className="skeleton mb-2 h-4 w-3/4 rounded" />
      <div className="skeleton h-4 w-1/2 rounded" />
    </div>
  );
}

export default function ABTestsPage() {
  const { tests, isLoading, error } = useABTests();

  const activeTests = tests.filter((t) =>
    ["COLLECTING", "WAITING", "ANALYZING", "DEPLOYING"].includes(t.state)
  );
  const completedTests = tests.filter((t) =>
    ["DECIDED", "COMPLETED", "INCONCLUSIVE", "ARCHIVED"].includes(t.state)
  );

  return (
    <div className="animate-fade-in px-6 py-8 lg:px-10">
      <div className="mb-8">
        <h1 className="font-display text-2xl font-bold text-foreground">
          A/B Tests
        </h1>
        <p className="mt-1 text-sm text-foreground-secondary">
          Monitor active experiments and review completed test results.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-card border border-error/30 bg-error-muted p-4 text-sm text-error" role="alert">
          {error}
        </div>
      )}

      {isLoading && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2" role="status">
          {Array.from({ length: 4 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {!isLoading && !error && (
        <>
          {activeTests.length > 0 && (
            <div className="mb-8">
              <h2 className="mb-4 text-lg font-semibold text-foreground">
                Active ({activeTests.length})
              </h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {activeTests.map((test) => (
                  <TestCard key={test.test_id} test={test} />
                ))}
              </div>
            </div>
          )}

          {completedTests.length > 0 && (
            <div>
              <h2 className="mb-4 text-lg font-semibold text-foreground">
                Completed ({completedTests.length})
              </h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                {completedTests.map((test) => (
                  <TestCard key={test.test_id} test={test} />
                ))}
              </div>
            </div>
          )}

          {tests.length === 0 && (
            <div className="flex flex-col items-center justify-center rounded-card border border-border-subtle bg-surface/50 px-6 py-16 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-elevated">
                <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted" aria-hidden="true">
                  <path d="M8 14h12M14 8v12" strokeLinecap="round" />
                </svg>
              </div>
              <h2 className="mb-1 text-base font-semibold text-foreground">No A/B tests yet</h2>
              <p className="max-w-sm text-sm text-muted">
                Use the chat panel to design and start an A/B test on any campaign.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Test card component
// ---------------------------------------------------------------------------

interface TestCardProps {
  test: {
    test_id: string;
    campaign_id: string;
    state: string;
    hypothesis: string;
    next_check_at?: string;
    current_metrics?: Record<string, Record<string, number>>;
  };
}

function TestCard({ test }: TestCardProps) {
  const stateClass = STATE_COLORS[test.state] ?? STATE_COLORS.DESIGNED;
  const isActive = ["COLLECTING", "WAITING", "ANALYZING", "DEPLOYING"].includes(test.state);

  return (
    <Link
      href={`/ab-tests/${encodeURIComponent(test.test_id)}`}
      className="block rounded-card border border-border bg-surface p-5 shadow-card transition-colors duration-fast hover:border-accent/40"
    >
      <div className="mb-3 flex items-center justify-between">
        <span className="text-sm font-semibold text-foreground truncate">
          {test.test_id}
        </span>
        <span className={`rounded-badge px-2 py-0.5 text-xs font-medium ${stateClass}`}>
          {test.state}
        </span>
      </div>

      <p className="mb-2 text-sm text-foreground-secondary line-clamp-2">
        {test.hypothesis || "No hypothesis specified"}
      </p>

      <p className="text-xs text-muted">Campaign: {test.campaign_id}</p>

      {isActive && test.next_check_at && (
        <p className="mt-2 text-xs text-muted tabular-nums">
          Next check: {new Date(test.next_check_at).toLocaleString("en-US", {
            month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
          })}
        </p>
      )}

      {test.current_metrics && Object.keys(test.current_metrics).length > 0 && (
        <div className="mt-3 flex gap-3">
          {Object.entries(test.current_metrics).map(([vid, metrics]) => (
            <div key={vid} className="rounded bg-elevated px-2 py-1 text-xs text-muted">
              <span className="font-medium text-foreground-secondary">{vid}</span>
              {" "}n={metrics.sample_size ?? "?"}
            </div>
          ))}
        </div>
      )}
    </Link>
  );
}
