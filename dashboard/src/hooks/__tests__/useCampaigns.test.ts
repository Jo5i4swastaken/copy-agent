import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useCampaigns, useCampaign } from "../useCampaigns";
import { mockCampaignSummaries, mockCampaign } from "@/test/fixtures";

beforeEach(() => {
  vi.restoreAllMocks();
});

describe("useCampaigns", () => {
  it("fetches and returns campaign list", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockCampaignSummaries), { status: 200 }),
    );

    const { result } = renderHook(() => useCampaigns());

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.campaigns).toHaveLength(2);
    expect(result.current.campaigns[0].campaign_id).toBe("spring-sale");
    expect(result.current.error).toBeNull();
  });

  it("passes channel filter as query param", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([mockCampaignSummaries[0]]), { status: 200 }),
    );

    renderHook(() => useCampaigns({ channel: "email" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("channel=email"),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
  });

  it("passes status filter as query param", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );

    renderHook(() => useCampaigns({ status: "active" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining("status=active"),
        expect.objectContaining({ signal: expect.any(AbortSignal) }),
      );
    });
  });

  it("handles fetch error", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "DB error" }), { status: 500 }),
    );

    const { result } = renderHook(() => useCampaigns());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.error).toBe("DB error");
    expect(result.current.campaigns).toHaveLength(0);
  });

  it("handles empty response", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify([]), { status: 200 }),
    );

    const { result } = renderHook(() => useCampaigns());

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.campaigns).toHaveLength(0);
    expect(result.current.error).toBeNull();
  });
});

describe("useCampaign", () => {
  it("fetches a single campaign by ID", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(JSON.stringify(mockCampaign), { status: 200 }),
    );

    const { result } = renderHook(() => useCampaign("spring-sale"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.campaign).not.toBeNull();
    expect(result.current.campaign?.brief.campaign_id).toBe("spring-sale");
    expect(result.current.campaign?.variants).toHaveLength(2);
  });

  it("handles 404", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce(
      new Response(null, { status: 404 }),
    );

    const { result } = renderHook(() => useCampaign("nonexistent"));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.campaign).toBeNull();
    expect(result.current.error).toContain("not found");
  });

  it("returns null when id is null", async () => {
    const { result } = renderHook(() => useCampaign(null));

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.campaign).toBeNull();
    expect(result.current.error).toBeNull();
  });
});
