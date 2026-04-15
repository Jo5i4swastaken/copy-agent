"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { ABTestState } from "./useABTests";

// ---------------------------------------------------------------------------
// useABTestMonitor — polls for tests past their next_check_at
// ---------------------------------------------------------------------------

interface UseABTestMonitorOptions {
  /** Active tests to monitor. */
  tests: ABTestState[];
  /** Callback fired when one or more tests are past their check time. */
  onTestsDue: (dueTests: ABTestState[]) => void;
  /** Poll interval in milliseconds. Defaults to 30000 (30s). */
  intervalMs?: number;
  /** Whether monitoring is enabled. Defaults to true. */
  enabled?: boolean;
}

/**
 * Monitors active A/B tests and fires a callback when any test is past
 * its `next_check_at` timestamp. Uses a polling interval to check
 * periodically without requiring a WebSocket connection.
 *
 * This hook does NOT automatically call the API to trigger a check.
 * The parent component is responsible for handling the `onTestsDue`
 * callback (e.g. calling `refresh()` or triggering a chat command).
 */
export function useABTestMonitor({
  tests,
  onTestsDue,
  intervalMs = 30000,
  enabled = true,
}: UseABTestMonitorOptions) {
  const [dueCount, setDueCount] = useState(0);
  const callbackRef = useRef(onTestsDue);
  callbackRef.current = onTestsDue;

  const testsRef = useRef(tests);
  testsRef.current = tests;

  const checkForDueTests = useCallback(() => {
    const now = new Date().toISOString();
    const activeStates = new Set([
      "COLLECTING",
      "DEPLOYING",
      "DESIGNED",
      "WAITING",
    ]);

    const dueTests = testsRef.current.filter((test) => {
      if (!activeStates.has(test.state.toUpperCase())) return false;
      if (!test.next_check_at) return false;
      return test.next_check_at <= now;
    });

    setDueCount(dueTests.length);

    if (dueTests.length > 0) {
      callbackRef.current(dueTests);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;

    // Run an initial check
    checkForDueTests();

    // Set up polling interval
    const timer = setInterval(checkForDueTests, intervalMs);

    return () => {
      clearInterval(timer);
    };
  }, [enabled, intervalMs, checkForDueTests]);

  return { dueCount };
}
