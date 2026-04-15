"use client";

import { useState, useEffect, useCallback } from "react";
import type { AggregatedMetrics } from "@/lib/types";

// ---------------------------------------------------------------------------
// useMetrics — fetch aggregated metrics for dashboard KPIs and charts
// ---------------------------------------------------------------------------

interface UseMetricsResult {
  metrics: AggregatedMetrics | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches aggregated metrics from `/api/metrics`.
 *
 * Returns totals, per-channel breakdowns, metric averages, and a
 * chronological timeline for charting. Call `refresh()` to re-fetch
 * after the agent logs new metrics.
 */
export function useMetrics(): UseMetricsResult {
  const [metrics, setMetrics] = useState<AggregatedMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchMetrics() {
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch("/api/metrics");

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: AggregatedMetrics = await res.json();
        if (!cancelled) {
          setMetrics(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load metrics",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchMetrics();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { metrics, isLoading, error, refresh };
}
