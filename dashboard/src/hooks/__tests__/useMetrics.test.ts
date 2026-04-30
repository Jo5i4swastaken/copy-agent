import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useMetrics } from "../useMetrics";

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useMetrics", () => {
  it(
    "times out and clears loading when the request hangs",
    async () => {
      vi.useFakeTimers();

    vi.spyOn(global, "fetch").mockImplementationOnce(((_url: any, init: any) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    }) as any);

      const { result } = renderHook(() => useMetrics());

    expect(result.current.isLoading).toBe(true);

      await act(async () => {
        await vi.advanceTimersByTimeAsync(15_000);
      });

      await act(async () => {
        await vi.runAllTimersAsync();
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBe("Request timed out");
    },
    10_000,
  );
});
