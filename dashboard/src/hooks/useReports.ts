"use client";

import { useState, useEffect, useCallback } from "react";

// ---------------------------------------------------------------------------
// Report types
// ---------------------------------------------------------------------------

export interface ReportSummary {
  report_id: string;
  type: string;
  title: string;
  summary: string;
  generated_at: string;
  campaign_ids: string[];
}

export interface ReportDetail {
  report_id: string;
  type: string;
  title: string;
  summary: string;
  generated_at: string;
  campaign_ids: string[];
  sections: ReportSection[];
  [key: string]: unknown;
}

export interface ReportSection {
  heading: string;
  content: string;
  data?: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// useReports — fetch reports list
// ---------------------------------------------------------------------------

interface UseReportsResult {
  reports: ReportSummary[];
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches the list of all reports from `/api/reports`.
 */
export function useReports(): UseReportsResult {
  const [reports, setReports] = useState<ReportSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchReports() {
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch("/api/reports");

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: ReportSummary[] = await res.json();
        if (!cancelled) {
          setReports(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(
            err instanceof Error ? err.message : "Failed to load reports",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchReports();

    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return { reports, isLoading, error, refresh };
}

// ---------------------------------------------------------------------------
// useReport — fetch a single report by ID
// ---------------------------------------------------------------------------

interface UseReportResult {
  report: ReportDetail | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Fetches a single report from `/api/reports/{reportId}`.
 */
export function useReport(
  reportId: string | null | undefined,
): UseReportResult {
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    if (!reportId) {
      setReport(null);
      setIsLoading(false);
      setError(null);
      return;
    }

    let cancelled = false;

    async function fetchReport() {
      setIsLoading(true);
      setError(null);

      try {
        const res = await fetch(
          `/api/reports/${encodeURIComponent(reportId!)}`,
        );

        if (res.status === 404) {
          if (!cancelled) {
            setReport(null);
            setError(`Report "${reportId}" not found`);
          }
          return;
        }

        if (!res.ok) {
          const body = await res.json().catch(() => null);
          throw new Error(
            body?.error ?? `Request failed with status ${res.status}`,
          );
        }

        const data: ReportDetail = await res.json();
        if (!cancelled) {
          setReport(data);
        }
      } catch (err) {
        if (!cancelled) {
          setReport(null);
          setError(
            err instanceof Error ? err.message : "Failed to load report",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    fetchReport();

    return () => {
      cancelled = true;
    };
  }, [reportId, refreshKey]);

  return { report, isLoading, error, refresh };
}
