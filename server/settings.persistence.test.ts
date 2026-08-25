import { describe, expect, it, vi } from "vitest";

let stored: any = null;
vi.mock("./db", () => ({
  getAppSettings: vi.fn(async () => stored),
  saveAppSettings: vi.fn(async (input: Record<string, unknown>) => {
    stored = { id: 1, ...input, updatedAt: new Date() };
    return stored;
  }),
}));

const { appRouter } = await import("./routers");

const adminContext = () => ({
  user: { id: 1, openId: "owner", name: "Owner", email: "owner@example.com", loginMethod: "test", role: "admin" as const, createdAt: new Date(), updatedAt: new Date(), lastSignedIn: new Date() },
  req: {} as any,
  res: {} as any,
});

describe("settings persistence contract", () => {
  it("round-trips editable brand and workflow preferences for an admin", async () => {
    stored = null;
    const caller = appRouter.createCaller(adminContext());
    await caller.settings.update({ brandName: "AungMin Studio", uploadLimitMb: 500, storagePolicy: "retained", enabledTools: ["script", "voice"], defaultPlatform: "TikTok", exportFormats: ["MP4", "SRT"] });
    const saved = await caller.settings.get();
    expect(saved).toMatchObject({ brandName: "AungMin Studio", uploadLimitMb: 500, storagePolicy: "retained", enabledTools: ["script", "voice"], defaultPlatform: "TikTok" });
  });

  it("returns the saved settings to a later workspace read", async () => {
    stored = { id: 1, brandName: "AungMin Movie Recap", uploadLimitMb: 200, storagePolicy: "session", enabledTools: "script,voice,export", defaultPlatform: "YouTube", exportFormats: "MP4,WAV,SRT" };
    const caller = appRouter.createCaller(adminContext());
    expect(await caller.settings.get()).toMatchObject({ brandName: "AungMin Movie Recap", uploadLimitMb: 200, storagePolicy: "session", defaultPlatform: "YouTube" });
  });
});
