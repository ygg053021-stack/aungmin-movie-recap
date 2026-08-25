import { describe, expect, it } from "vitest";
import { canShowFinalOutput, clampTime, deriveSourceState, detectPlatform, formatTime, getReviewUrl, getYouTubeEmbedUrl } from "./editorState";

describe("editor state helpers", () => {
  it("formats and clamps timeline positions", () => {
    expect(formatTime(65)).toBe("01:05");
    expect(clampTime(-2, 60)).toBe(0);
    expect(clampTime(75, 60)).toBe(60);
    expect(clampTime(12.5, 60)).toBe(12.5);
  });

  it("accepts secure review links and rejects non-http links", () => {
    expect(getReviewUrl("https://youtube.com/shorts/abc123")).toBe("https://youtube.com/shorts/abc123");
    expect(() => getReviewUrl("javascript:alert(1)")).toThrow();
  });

  it("detects supported link platforms and models blocked/failed states", () => {
    expect(detectPlatform("https://youtube.com/shorts/abc")).toBe("YouTube");
    expect(detectPlatform("https://www.tiktok.com/@a/video/1")).toBe("TikTok");
    expect(detectPlatform("https://www.bilibili.com/video/BV1")).toBe("Bilibili");
    expect(detectPlatform("https://www.xiaohongshu.com/explore/1")).toBe("RedNote");
    expect(deriveSourceState(false, "", false, "blocked")).toBe("blocked");
    expect(deriveSourceState(false, "", false, "failed")).toBe("failed");
  });

  it("tracks source states and never treats an unverified output as ready", () => {
    expect(deriveSourceState(false, "")).toBe("empty");
    expect(deriveSourceState(false, "https://youtube.com/shorts/abc")).toBe("review-ready");
    expect(deriveSourceState(true, "")).toBe("upload-ready");
    expect(deriveSourceState(false, "", true)).toBe("invalid");
    expect(canShowFinalOutput(null, true)).toBe(false);
    expect(canShowFinalOutput("blob:final", false)).toBe(false);
    expect(canShowFinalOutput("blob:final", true)).toBe(true);
  });

  it("converts YouTube Shorts and watch links to privacy-enhanced embeds", () => {
    expect(getYouTubeEmbedUrl("https://youtube.com/shorts/fQeEDjColak?si=test")).toBe("https://www.youtube-nocookie.com/embed/fQeEDjColak?rel=0");
    expect(getYouTubeEmbedUrl("https://www.youtube.com/watch?v=pDDohu7oMPU")).toBe("https://www.youtube-nocookie.com/embed/pDDohu7oMPU?rel=0");
    expect(getYouTubeEmbedUrl("https://example.com/video")).toBeNull();
  });
});
