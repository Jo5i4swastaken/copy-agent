"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Campaign, CampaignSummary, Channel } from "@/lib/types";

// ---------------------------------------------------------------------------
// useCampaigns — fetch the campaign list with optional filters
// ---------------------------------------------------------------------------

interface UseCampaignsFilters {
  channel?: Channel;
  status?: string;
}

interface UseCampaignsResult {
  campaigns: CampaignSummary[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches the campaign list from `/api/campaigns`.
 *
 * Supports optional `channel` and `status` filters that are sent as query
 * parameters. Call `refresh()` to re-fetch (e.g. after the agent creates
 * a new campaign).
 */
export function useCampaigns(filters?: UseCampaignsFilters): UseCampaignsResult {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Stabilize filters reference to avoid infinite effect loops
  const filtersRef = useRef(filters);
  filtersRef.current = filters;

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchCampaigns() {
      setIsLoading(true);
      setError(null);

      try {
        const params = new URLSearchParams();
        if (filtersRef.current?.channel) {
          params.set("channel", filtersRef.current.channel);
        }
        if (filtersRef.current?.status) {
          params.set("status", filtersRef.current.status);
        }

        const qs = params.toString();
        const url = qs ? `/api/campaigns?${qs}` : "/api/campaigns";
        const res = await fetch(url);

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: CampaignSummary[] = await res.json();
        if (!cancelled) {
          setCampaigns(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load campaigns",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchCampaigns();

    return () => {
      cancelled = true;
    };
  }, [refreshKey, filters?.channel, filters?.status]);

  return { campaigns, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useCampaign — fetch a single campaign by id
// ---------------------------------------------------------------------------

interface UseCampaignResult {
  campaign: Campaign | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches a single campaign (brief + variants + metrics) from
 * `/api/campaigns/{id}`.
 *
 * Returns `campaign: null` while loading or if the campaign was not found.
 * Check `error` to distinguish between loading, not-found, and other errors.
 */
export function useCampaign(id: string | null | undefined): UseCampaignResult {
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!id) {
      setCampaign(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    async function fetchCampaign() {
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(`/api/campaigns/${encodeURIComponent(id!)}`);

        if (res.status === 404) {
          if (!cancelled) {
            setCampaign(null);
            setError(`Campaign "${id}" not found`);
          }
          return;
        }

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: Campaign = await res.json();
        if (!cancelled) {
          setCampaign(data);
        }
      } catch (err) {
        if (!cancelled) {
          setCampaign(null);
          setError(
            err instanceof Error ? err.message : "Failed to load campaign",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchCampaign();

    return () => {
      cancelled = true;
    };
  }, [id, refreshKey]);

  return { campaign, isLoading, error, refresh };
}
