import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useABTests, useABTest } from "../useABTests";
import { mockABTestCollecting, mockABTestDecided } from "@/test/fixtures";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useABTests", () => {
  it("fetches and returns tests", async () => {
    const mockTests = [mockABTestCollecting, mockABTestDecided];
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockTests), { status: 200 }),
    );

    const { result } = renderHook(() => useABTests());

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tests).toHaveLength(2);
    expect(result.current.tests[0].test_id).toBe("test-001");
    expect(result.current.tests[1].state).toBe("DECIDED");
    expect(result.current.error).toBeNull();
  });

  it("handles fetch error", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "Server error" }), { status: 500 }),
    );

    const { result } = renderHook(() => useABTests());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tests).toHaveLength(0);
    expect(result.current.error).toBe("Server error");
  });

  it("handles network error", async () => {
    vi.spyOn(global, "fetch").mockRejectedValueOnce(new Error("Network failure"));

    const { result } = renderHook(() => useABTests());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("Network failure");
  });

  it("handles empty response", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );

    const { result } = renderHook(() => useABTests());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.tests).toHaveLength(0);
    expect(result.current.error).toBeNull();
  });
});

describe("useABTest", () => {
  it("returns the matching test by ID", async () => {
    const mockTests = [mockABTestCollecting, mockABTestDecided];
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockTests), { status: 200 }),
    );

    const { result } = renderHook(() => useABTest("test-002"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.test).not.toBeNull();
    expect(result.current.test?.test_id).toBe("test-002");
    expect(result.current.test?.state).toBe("DECIDED");
  });

  it("returns null for non-existent ID", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([mockABTestCollecting]), { status: 200 }),
    );

    const { result } = renderHook(() => useABTest("nonexistent"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.test).toBeNull();
  });

  it("returns null when testId is null", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );

    const { result } = renderHook(() => useABTest(null));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.test).toBeNull();
  });
});
