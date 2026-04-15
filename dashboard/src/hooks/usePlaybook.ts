"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Playbook } from "@/lib/types";

// ---------------------------------------------------------------------------
// usePlaybook — fetch the marketing playbook with optional category filter
// ---------------------------------------------------------------------------

interface UsePlaybookResult {
  playbook: Playbook | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches the marketing playbook from `/api/playbook`.
 *
 * When `category` is provided, only learnings matching that category are
 * returned (sorted by confidence, highest first).
 *
 * Call `refresh()` to re-fetch after the agent updates the playbook.
 */
export function usePlaybook(category?: string): UsePlaybookResult {
  const [playbook, setPlaybook] = useState<Playbook | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Stabilize category reference to avoid infinite effect loops
  const categoryRef = useRef(category);
  categoryRef.current = category;

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchPlaybook() {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (categoryRef.current) {
          params.set("category", categoryRef.current);
        }

        const qs = params.toString();
        const url = qs ? `/api/playbook?${qs}` : "/api/playbook";
        const res = await fetch(url);

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: Playbook = await res.json();
        if (!cancelled) {
          setPlaybook(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load playbook",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchPlaybook();

    return () => {
      cancelled = true;
    };
  }, [refreshKey, category]);

  return { playbook, isLoading, error, refresh };
}
