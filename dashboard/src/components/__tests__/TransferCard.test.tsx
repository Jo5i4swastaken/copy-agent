import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TransferCard } from "../cross-channel/TransferCard";
import { mockTransferProposed, mockTransferConfirmed } from "@/test/fixtures";

describe("TransferCard", () => {
  it("renders source and target channels", () => {
    render(<TransferCard transfer={mockTransferProposed} />);

    expect(screen.getByText("email")).toBeInTheDocument();
    expect(screen.getByText("sms")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    render(<TransferCard transfer={mockTransferProposed} />);

    expect(screen.getByText("proposed")).toBeInTheDocument();
  });

  it("renders hypothesis text", () => {
    render(<TransferCard transfer={mockTransferProposed} />);

    expect(
      screen.getByText(/Playful tone from email/),
    ).toBeInTheDocument();
  });

  it("renders learning text when provided", () => {
    render(<TransferCard transfer={mockTransferProposed} />);

    expect(
      screen.getByText(/Playful tone increases engagement/),
    ).toBeInTheDocument();
  });

  it("renders created date", () => {
    render(<TransferCard transfer={mockTransferProposed} />);

    expect(screen.getByText(/Apr 2, 2026/)).toBeInTheDocument();
  });

  it("renders confirmed status with correct styling class", () => {
    render(<TransferCard transfer={mockTransferConfirmed} />);

    const badge = screen.getByText("confirmed");
    expect(badge).toBeInTheDocument();
  });

  it("renders without optional fields", () => {
    const minimal = {
      transfer_id: "tf-min",
      source_channel: "seo",
      target_channel: "ad",
      hypothesis: "Test hypothesis",
      status: "testing",
    };

    render(<TransferCard transfer={minimal} />);

    expect(screen.getByText("seo")).toBeInTheDocument();
    expect(screen.getByText("ad")).toBeInTheDocument();
    expect(screen.getByText("testing")).toBeInTheDocument();
  });
});
