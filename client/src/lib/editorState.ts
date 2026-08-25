export type EditorPanel = "source" | "recap" | "voice" | "finish";

export const formatTime = (value: number) => `${Math.floor(value / 60).toString().padStart(2, "0")}:${Math.floor(value % 60).toString().padStart(2, "0")}`;

export const clampTime = (value: number, duration: number) => Math.max(0, Math.min(duration || 0, value));

export const getReviewUrl = (value: string) => {
  const parsed = new URL(value.trim());
  if (!/^https?:$/.test(parsed.protocol)) throw new Error("Unsupported URL protocol");
  return parsed.toString();
};

export type SourceState = "empty" | "invalid" | "unsupported" | "fetching" | "fetched" | "review-ready" | "blocked" | "failed" | "upload-ready";
export type SourcePlatform = "YouTube" | "TikTok" | "Bilibili" | "RedNote" | "Unknown";

export const detectPlatform = (value: string): SourcePlatform => {
  const host = new URL(value).hostname.replace(/^www\./, "");
  if (host === "youtube.com" || host.endsWith("youtube.com") || host === "youtu.be") return "YouTube";
  if (host === "tiktok.com" || host.endsWith("tiktok.com")) return "TikTok";
  if (host === "bilibili.com" || host.endsWith("bilibili.com")) return "Bilibili";
  if (host === "rednote.com" || host.endsWith("xiaohongshu.com")) return "RedNote";
  return "Unknown";
};

export const deriveSourceState = (hasFile: boolean, reviewUrl: string, hasInvalidInput = false, state?: SourceState): SourceState => {
  if (hasFile) return "upload-ready";
  if (state && state !== "empty") return state;
  if (reviewUrl) return "review-ready";
  if (hasInvalidInput) return "invalid";
  return "empty";
};

export const canShowFinalOutput = (outputUrl: string | null, verified: boolean) => Boolean(outputUrl && verified);

export const getYouTubeEmbedUrl = (value: string) => {
  const parsed = new URL(value);
  const host = parsed.hostname.replace(/^www\./, "");
  if (host !== "youtube.com" && host !== "youtu.be" && !host.endsWith(".youtube.com")) return null;
  const id = host === "youtu.be" ? parsed.pathname.split("/").filter(Boolean)[0] : parsed.pathname.startsWith("/shorts/") ? parsed.pathname.split("/")[2] : parsed.searchParams.get("v");
  return id ? `https://www.youtube-nocookie.com/embed/${encodeURIComponent(id)}?rel=0` : null;
};
