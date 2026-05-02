import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { ChatPanel } from "@/components/layout/ChatPanel";

class MockWebSocket {
  static instances: MockWebSocket[] = [];

  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: ((event: unknown) => void) | null = null;
  onclose: (() => void) | null = null;
  send = vi.fn();
  close = vi.fn(() => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.();
  });

  constructor(_url: string) {
    MockWebSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = MockWebSocket.OPEN;
      this.onopen?.();
    });
  }
}

function TestHarness() {
  const [open, setOpen] = useState(false);
  return <ChatPanel isOpen={open} onToggle={() => setOpen((v) => !v)} />;
}

function findStartRunPayload(ws: MockWebSocket) {
  const calls = ws.send.mock.calls
    .map((c) => c[0])
    .filter((m) => typeof m === "string") as string[];
  const parsed = calls.map((m) => {
    try {
      return JSON.parse(m) as any;
    } catch {
      return null;
    }
  });
  return parsed.find((p) => p?.method === "start_run") ?? null;
}

describe("Chat attachments (acceptance)", () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal("WebSocket", MockWebSocket as unknown as typeof WebSocket);
    if (!URL.createObjectURL) {
      vi.stubGlobal("URL", {
        ...URL,
        createObjectURL: vi.fn(() => "blob:mock"),
        revokeObjectURL: vi.fn(),
      });
    }
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("supports attaching files with previews, sends attachments, and resets", async () => {
    const user = userEvent.setup();
    render(<TestHarness />);

    await user.click(screen.getByRole("button", { name: /Open chat panel/i }));

    await waitFor(() => {
      expect(MockWebSocket.instances.length).toBeGreaterThan(0);
    });
    const ws = MockWebSocket.instances[0];

    await waitFor(() => {
      expect(ws.send).toHaveBeenCalled();
    });

    const fileInput = screen.getByLabelText("File attachment") as HTMLInputElement;

    const pngBytes = Uint8Array.from([
      137, 80, 78, 71, 13, 10, 26, 10, 0, 0, 0, 13, 73, 72, 68, 82, 0, 0, 0,
      1, 0, 0, 0, 1, 8, 6, 0, 0, 0, 31, 21, 196, 137, 0, 0, 0, 10, 73, 68,
      65, 84, 120, 156, 99, 0, 1, 0, 0, 5, 0, 1, 13, 10, 45, 180, 0, 0, 0,
      0, 73, 69, 78, 68, 174, 66, 96, 130,
    ]);
    const imageFile = new File([pngBytes], "tiny.png", { type: "image/png" });
    fireEvent.change(fileInput, { target: { files: [imageFile] } });

    expect(await screen.findByTestId("attachment-preview")).toBeInTheDocument();
    expect(await screen.findByTestId("attachment-preview-image")).toBeInTheDocument();
    expect(screen.getByText("tiny.png")).toBeInTheDocument();

    const textarea = screen.getByLabelText("Message input");
    await user.type(textarea, "Here is an image");
    expect(screen.getByTestId("attachment-preview")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Send message/i }));

    await waitFor(() => {
      const payload = findStartRunPayload(ws);
      expect(payload).not.toBeNull();
      expect(payload.params.prompt).toBe("Here is an image");
      expect(payload.params.attachments).toHaveLength(1);
      expect(payload.params.attachments[0].name).toBe("tiny.png");
      expect(payload.params.attachments[0].mime).toBe("image/png");
      expect(typeof payload.params.attachments[0].data_base64).toBe("string");
      expect(payload.params.attachments[0].data_base64.length).toBeGreaterThan(0);
    });

    expect(screen.queryByTestId("attachment-preview")).toBeNull();
    expect((screen.getByLabelText("Message input") as HTMLTextAreaElement).value).toBe(
      "",
    );

    const textFile = new File(["Hello world"], "note.txt", { type: "text/plain" });
    fireEvent.change(fileInput, { target: { files: [textFile] } });
    expect(await screen.findByTestId("attachment-preview-text")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Remove attachment/i }));
    expect(screen.queryByTestId("attachment-preview")).toBeNull();

    const binaryFile = new File([Uint8Array.from([0, 255, 1, 254])], "data.bin", {
      type: "application/octet-stream",
    });
    fireEvent.change(fileInput, { target: { files: [binaryFile] } });
    expect(await screen.findByTestId("attachment-preview-generic")).toBeInTheDocument();
    expect(screen.getByText("data.bin")).toBeInTheDocument();
  });
});
