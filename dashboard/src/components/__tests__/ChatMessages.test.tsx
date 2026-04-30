import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChatMessages from "../chat/ChatMessages";
import type { ChatMessage } from "@/lib/types";

describe("ChatMessages", () => {
  it("does not render tool approval UI for non-approval tool activity messages", () => {
    const messages: ChatMessage[] = [
      {
        id: "msg-1",
        role: "system",
        content: "Calling tool: foo",
        timestamp: new Date().toISOString(),
        tool_activity: [
          {
            tool_name: "foo",
            arguments: { a: 1 },
            status: "calling",
          },
        ],
      },
    ];

    render(<ChatMessages messages={messages} isRunning={false} />);

    expect(screen.queryByRole("button", { name: /Approve/i })).toBeNull();
    expect(screen.queryByRole("button", { name: /Deny/i })).toBeNull();
    expect(screen.getByText("Calling tool: foo")).toBeInTheDocument();
  });

  it("strips the approval prefix before calling onApproveToolCall", async () => {
    const user = userEvent.setup();
    const onApproveToolCall = vi.fn();

    const messages: ChatMessage[] = [
      {
        id: "approval-req-123",
        role: "system",
        content: "Approve tool: foo?",
        timestamp: new Date().toISOString(),
        tool_activity: [
          {
            tool_name: "foo",
            arguments: { a: 1 },
            status: "calling",
          },
        ],
      },
    ];

    render(
      <ChatMessages
        messages={messages}
        isRunning={false}
        onApproveToolCall={onApproveToolCall}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Approve foo/i }));

    expect(onApproveToolCall).toHaveBeenCalledWith("req-123", true);
  });
});
