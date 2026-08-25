import { describe, expect, it } from "vitest";
import { DEFAULT_MOVIE_RECAP_CONFIG, normalizeMovieRecapConfig } from "../shared/movieRecapConfig";
import { appRouter } from "./routers";

describe("movie recap configuration", () => {
  it("uses the AungMin brand and safe defaults", () => {
    expect(DEFAULT_MOVIE_RECAP_CONFIG.brandName).toBe("AungMin Movie Recap");
    expect(DEFAULT_MOVIE_RECAP_CONFIG.uploadLimitMb).toBe(200);
    expect(DEFAULT_MOVIE_RECAP_CONFIG.storagePolicy).toBe("session");
  });

  it("normalizes editable settings without accepting invalid values", () => {
    expect(normalizeMovieRecapConfig({ brandName: "  My Studio  ", uploadLimitMb: 5000, storagePolicy: "retained", theme: "indigo-rose", defaultPlatform: "TikTok", enabledTools: ["voice", "unknown"] })).toEqual({
      brandName: "My Studio",
      theme: "indigo-rose",
      uploadLimitMb: 2048,
      storagePolicy: "retained",
      defaultPlatform: "TikTok",
      enabledTools: ["voice"],
      exportFormats: ["MP4", "WAV", "SRT"],
    });
  });

  it("falls back when input is missing or malformed", () => {
    expect(normalizeMovieRecapConfig({ brandName: "", uploadLimitMb: -2, enabledTools: [] })).toEqual(DEFAULT_MOVIE_RECAP_CONFIG);
  });
});

  it("exposes a safe AI readiness status without returning credentials", async () => {
    const caller = appRouter.createCaller({ user: undefined, req: {} as any, res: {} as any });
    const status = await caller.recap.status();
    expect(status).toHaveProperty("ready");
    expect(status).not.toHaveProperty("key");
  });

  it("accepts a complete export manifest", async () => {
    const caller = appRouter.createCaller({ user: undefined, req: {} as any, res: {} as any });
    const result = await caller.export.prepare({ requestedFormat: "MP4", platform: "YouTube", ratio: "16:9", voice: { name: "Chiron", style: "cinematic narrator", speed: "1×", timingBasis: "Audio duration" }, subtitles: { font: "Noto Sans Myanmar", size: 34, color: "#ffffff", background: "Transparent", outline: "Soft outline", position: "Bottom" }, overlays: { logo: null, music: null }, blur: null });
    expect(result.accepted).toBe(true);
    expect(result.formats).toEqual(["MP4", "WAV", "SRT"]);
  });

  it("validates upload size against the configured limit", async () => {
    const { isUploadWithinLimit } = await import("../shared/movieRecapConfig");
    expect(isUploadWithinLimit(50 * 1024 * 1024, 200)).toBe(true);
    expect(isUploadWithinLimit(201 * 1024 * 1024, 200)).toBe(false);
  });

  it("normalizes persisted preference values safely", () => {
    const saved = normalizeMovieRecapConfig({ brandName: "  Studio  ", uploadLimitMb: 500, storagePolicy: "retained", defaultPlatform: "TikTok", enabledTools: ["voice", "voice", "unknown"] });
    expect(saved).toMatchObject({ brandName: "Studio", uploadLimitMb: 500, storagePolicy: "retained", defaultPlatform: "TikTok", enabledTools: ["voice"] });
  });

  it("rejects non-admin settings updates before database access", async () => {
    const caller = appRouter.createCaller({ user: { id: 1, openId: "user", name: "User", email: "user@example.com", loginMethod: "test", role: "user", createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() }, req: {} as any, res: {} as any });
    await expect(caller.settings.update({ brandName: "Nope" })).rejects.toMatchObject({ code: "FORBIDDEN" });
  });
