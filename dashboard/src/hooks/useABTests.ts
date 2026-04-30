"use client";

import { useState, useEffect, useCallback } from "react";

const REQUEST_TIMEOUT_MS = 15_000;

// ---------------------------------------------------------------------------
// A/B Test types (client-side mirrors of API response)
// ---------------------------------------------------------------------------

export interface ABTestCheck {
  check_number: number;
  checked_at: string;
  control_value: number;
  treatment_value: number;
  p_value: number | null;
  effect_size: number | null;
  verdict: string;
  sample_size_control: number;
  sample_size_treatment: number;
}

export interface ABTestResult {
  winner: string | null;
  p_value: number | null;
  effect_size: number | null;
  confidence_interval: [number, number] | null;
  concluded_at: string;
  reason: string;
}

export interface ABTestState {
  test_id: string;
  campaign_id: string;
  state: string;
  hypothesis: string;
  control_variant_id: string;
  treatment_variant_id: string;
  metric_type: string;
  created_at: string;
  next_check_at: string | null;
  max_duration_hours: number;
  checks: ABTestCheck[];
  result: ABTestResult | null;
}

// ---------------------------------------------------------------------------
// useABTests — fetch all A/B tests
// ---------------------------------------------------------------------------

interface UseABTestsResult {
  tests: ABTestState[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches the list of all A/B tests from `/api/ab-tests`.
 * Call `refresh()` to re-fetch.
 */
export function useABTests(): UseABTestsResult {
  const [tests, setTests] = useState<ABTestState[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchTests() {
      setIsLoading(true);
      setError(null);

      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

        const res = await fetch("/api/ab-tests", { signal: controller.signal });
        clearTimeout(timeout);

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: ABTestState[] = await res.json();
        if (!cancelled) {
          setTests(data);
        }
      } catch (err) {
        if (!cancelled) {
          if (err instanceof DOMException && err.name === "AbortError") {
            setError("Request timed out");
          } else {
            setError(
              err instanceof Error ? err.message : "Failed to load A/B tests",
            );
          }
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchTests();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { tests, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useABTest — fetch a single A/B test by ID (from the full list)
// ---------------------------------------------------------------------------

interface UseABTestResult {
  test: ABTestState | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches all tests and filters to the one matching `testId`.
 * Returns `test: null` while loading or if not found.
 */
export function useABTest(testId: string | null | undefined): UseABTestResult {
  const { tests, isLoading, error, refresh } = useABTests();

  const test = testId
    ? tests.find((t) => t.test_id === testId) ?? null
    : null;

  return { test, isLoading, error, refresh };
}
