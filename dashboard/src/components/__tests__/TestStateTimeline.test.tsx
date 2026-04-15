import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TestStateTimeline } from "../ab-test/TestStateTimeline";

describe("TestStateTimeline", () => {
  it("renders all 5 states", () => {
    render(
      <TestStateTimeline
        currentState="COLLECTING"
        createdAt="2026-04-01T10:00:00"
      />,
    );

    expect(screen.getByText("Designed")).toBeInTheDocument();
    expect(screen.getByText("Deploying")).toBeInTheDocument();
    expect(screen.getByText("Collecting")).toBeInTheDocument();
    expect(screen.getByText("Decided")).toBeInTheDocument();
    expect(screen.getByText("Completed")).toBeInTheDocument();
  });

  it("marks current state with aria-current", () => {
    render(
      <TestStateTimeline
        currentState="COLLECTING"
        createdAt="2026-04-01T10:00:00"
      />,
    );

    const items = screen.getAllByRole("listitem");
    // COLLECTING is index 2
    expect(items[2]).toHaveAttribute("aria-current", "step");
    // Others should not have aria-current
    expect(items[0]).not.toHaveAttribute("aria-current");
    expect(items[4]).not.toHaveAttribute("aria-current");
  });

  it("renders the timeline container with role=list", () => {
    render(
      <TestStateTimeline
        currentState="DESIGNED"
        createdAt="2026-04-01T10:00:00"
      />,
    );

    expect(screen.getByRole("list")).toBeInTheDocument();
  });

  it("shows timestamps when provided", () => {
    render(
      <TestStateTimeline
        currentState="DECIDED"
        createdAt="2026-04-01T10:00:00"
        timestamps={{
          DEPLOYING: "2026-04-01T12:00:00",
          COLLECTING: "2026-04-01T12:05:00",
          DECIDED: "2026-04-03T10:00:00",
        }}
      />,
    );

    // Multiple Apr 1 timestamps exist (created, DEPLOYING, COLLECTING)
    expect(screen.getAllByText(/Apr 1/).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Apr 3/)).toBeInTheDocument();
  });

  it("handles COMPLETED state", () => {
    render(
      <TestStateTimeline
        currentState="COMPLETED"
        createdAt="2026-04-01T10:00:00"
      />,
    );

    const items = screen.getAllByRole("listitem");
    expect(items[4]).toHaveAttribute("aria-current", "step");
  });

  it("handles unknown state gracefully", () => {
    render(
      <TestStateTimeline
        currentState="UNKNOWN"
        createdAt="2026-04-01T10:00:00"
      />,
    );

    // Should still render all states, none should be current
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(5);
    items.forEach((item) => {
      expect(item).not.toHaveAttribute("aria-current");
    });
  });
});
