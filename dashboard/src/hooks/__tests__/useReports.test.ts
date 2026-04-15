import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useReports, useReport } from "../useReports";
import { mockReportSummaries, mockReportDetail } from "@/test/fixtures";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useReports", () => {
  it("fetches and returns reports list", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockReportSummaries), { status: 200 }),
    );

    const { result } = renderHook(() => useReports());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.reports).toHaveLength(2);
    expect(result.current.reports[0].report_id).toBe("report-playbook-001");
    expect(result.current.reports[1].type).toBe("campaign_performance");
    expect(result.current.error).toBeNull();
  });

  it("handles empty list", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );

    const { result } = renderHook(() => useReports());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.reports).toHaveLength(0);
    expect(result.current.error).toBeNull();
  });

  it("handles server error", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Internal error" }), { status: 500 }),
    );

    const { result } = renderHook(() => useReports());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Internal error");
  });
});

describe("useReport", () => {
  it("fetches a single report by ID", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockReportDetail), { status: 200 }),
    );

    const { result } = renderHook(() => useReport("report-perf-001"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.report).not.toBeNull();
    expect(result.current.report?.report_id).toBe("report-perf-001");
    expect(result.current.report?.sections).toHaveLength(2);
  });

  it("handles 404 not found", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(null, { status: 404 }),
    );

    const { result } = renderHook(() => useReport("nonexistent"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.report).toBeNull();
    expect(result.current.error).toContain("not found");
  });

  it("returns null when reportId is null", async () => {
    const { result } = renderHook(() => useReport(null));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.report).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
