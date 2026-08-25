// @vitest-environment jsdom
import React from "react";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  generate: vi.fn(),
  prepare: vi.fn(),
}));

vi.mock("@/lib/trpc", () => ({
  trpc: {
    recap: { generate: { useMutation: () => ({ mutateAsync: mocks.generate }) } },
    export: { prepare: { useMutation: () => ({ mutateAsync: mocks.prepare }) } },
  },
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

import Home from "./Home";

describe("Home editor source flow", () => {
  afterEach(() => cleanup());

  beforeEach(() => {
    vi.clearAllMocks();
    Object.defineProperty(URL, "createObjectURL", { value: vi.fn(() => "blob:test-video"), configurable: true });
    Object.defineProperty(URL, "revokeObjectURL", { value: vi.fn(), configurable: true });
  });

  it("starts empty and changes to review-ready for a valid YouTube Shorts link", () => {
    render(<Home />);
    expect(screen.getByText("WAITING")).toBeTruthy();
    fireEvent.change(screen.getByPlaceholderText("YouTube / TikTok / Bilibili / RedNote link"), { target: { value: "https://youtube.com/shorts/fQeEDjColak" } });
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(screen.getByText("REVIEW READY")).toBeTruthy();
    expect(screen.getByTitle("Video link review")).toBeTruthy();
  });

  it("rejects an invalid link without changing the empty source state", () => {
    render(<Home />);
    fireEvent.change(screen.getByPlaceholderText("YouTube / TikTok / Bilibili / RedNote link"), { target: { value: "not-a-url" } });
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(screen.getByText("INVALID")).toBeTruthy();
  });

  it("keeps finish state as export accepted until a verified output exists", async () => {
    mocks.generate.mockResolvedValue({ script: "မြန်မာ recap စာသား။", mode: "server-ai" });
    mocks.prepare.mockResolvedValue({ accepted: true, note: "Export manifest validated." });
    render(<Home />);
    fireEvent.change(screen.getByPlaceholderText("Paste your Gemini API key"), { target: { value: "test-key" } });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const video = new File([new Uint8Array([0, 1, 2])], "movie.mp4", { type: "video/mp4" });
    fireEvent.change(input, { target: { files: [video] } });
    fireEvent.click(screen.getAllByRole("button", { name: /RECAP/i })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Quick Recap/i }));
    await waitFor(() => expect(mocks.generate).toHaveBeenCalled());
    expect(screen.getByText("မြန်မာအသံ", { exact: false })).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: /FINISH/i })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Prepare final recap export/i }));
    expect(await screen.findByText("Export request accepted")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Download Myanmar SRT" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "MP4 rendering pending" })).toBeTruthy();
    expect(screen.getByText("WAV မရသေးပါ", { exact: false })).toBeTruthy();
    expect(screen.queryByText("Final output verified")).toBeNull();
  });

  it("changes to upload-ready and opens the recap panel after a video file is selected", () => {
    render(<Home />);
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const video = new File([new Uint8Array([0, 1, 2])], "movie.mp4", { type: "video/mp4" });
    fireEvent.change(input, { target: { files: [video] } });
    expect(screen.getByText("UPLOAD READY")).toBeTruthy();
    fireEvent.click(screen.getAllByRole("button", { name: /RECAP/i })[0]);
    expect(screen.getByText("မြန်မာ Recap")).toBeTruthy();
  });
});


describe("verified output branch", () => {
  afterEach(() => cleanup());

  it("shows final output verified only when the server returns a verified output URL", async () => {
    mocks.generate.mockResolvedValue({ script: "မြန်မာ recap စာသား။", mode: "server-ai" });
    mocks.prepare.mockResolvedValue({ accepted: true, ready: true, outputUrl: "blob:verified-final" });
    render(<Home />);
    fireEvent.change(screen.getByPlaceholderText("Paste your Gemini API key"), { target: { value: "test-key" } });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const video = new File([new Uint8Array([0, 1, 2])], "movie.mp4", { type: "video/mp4" });
    fireEvent.change(input, { target: { files: [video] } });
    fireEvent.click(screen.getAllByRole("button", { name: /RECAP/i })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Quick Recap/i }));
    await waitFor(() => expect(mocks.generate).toHaveBeenCalled());
    fireEvent.click(screen.getAllByRole("button", { name: /FINISH/i })[0]);
    fireEvent.click(screen.getByRole("button", { name: /Prepare final recap export/i }));
    expect(await screen.findByText("Final output verified")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Download MP4" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Download Myanmar SRT" })).toBeTruthy();
    expect(screen.getByText("WAV မရသေးပါ", { exact: false })).toBeTruthy();
  });
});
