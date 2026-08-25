import { COOKIE_NAME } from "@shared/const";
import { getSessionCookieOptions } from "./_core/cookies";
import { systemRouter } from "./_core/systemRouter";
import { adminProcedure, publicProcedure, router } from "./_core/trpc";
import { getAppSettings, saveAppSettings } from "./db";
import { z } from "zod";
import { invokeLLM } from "./_core/llm";

const exportPayloadInput = z.object({ platform: z.string(), ratio: z.string(), voice: z.object({ name: z.string(), style: z.string(), speed: z.string(), timingBasis: z.string() }), subtitles: z.object({ font: z.string(), size: z.number(), color: z.string(), background: z.string(), outline: z.string(), position: z.string() }), overlays: z.object({ logo: z.object({ url: z.string().nullable(), position: z.string() }).nullable(), music: z.object({ name: z.string(), size: z.number() }).nullable() }), blur: z.object({ regions: z.string(), frame: z.string(), x: z.number(), y: z.number(), width: z.number(), height: z.number() }).nullable() });
const settingsInput = z.object({
  brandName: z.string().max(120).optional(), logoUrl: z.string().max(2_000_000).nullable().optional(), faviconUrl: z.string().max(2_000_000).nullable().optional(), theme: z.enum(["violet-teal", "indigo-rose"]).optional(), uploadLimitMb: z.number().int().min(10).max(2048).optional(), storagePolicy: z.enum(["session", "retained"]).optional(), enabledTools: z.array(z.string()).optional(), defaultPlatform: z.enum(["YouTube", "TikTok", "Facebook"]).optional(), exportFormats: z.array(z.enum(["MP4", "WAV", "SRT"])).optional(),
});

export const appRouter = router({
  system: systemRouter,
  auth: router({
    me: publicProcedure.query(opts => opts.ctx.user),
    logout: publicProcedure.mutation(({ ctx }) => { const cookieOptions = getSessionCookieOptions(ctx.req); ctx.res.clearCookie(COOKIE_NAME, { ...cookieOptions, maxAge: -1 }); return { success: true } as const; }),
  }),
  recap: router({
    status: publicProcedure.query(() => ({ ready: Boolean(process.env.BUILT_IN_FORGE_API_KEY), mode: process.env.BUILT_IN_FORGE_API_KEY ? "server-ai" : "demo-fallback" as const })),
    generate: publicProcedure.input(z.object({ language: z.string(), voiceStyle: z.string(), audioSpeed: z.string().optional(), timingBasis: z.string().optional(), platform: z.string(), durationHint: z.string().optional() })).mutation(async ({ input }) => {
      if (!process.env.BUILT_IN_FORGE_API_KEY) return { script: "AI configuration is not ready. Use the local draft mode and add a server secret when you are ready.", mode: "demo-fallback" as const };
      const response = await invokeLLM({ messages: [{ role: "system", content: "You write concise, cinematic movie recap narration. Return only the narration text, no headings or markdown." }, { role: "user", content: `Create a cinematic movie recap narration in ${input.language}. Style: ${input.voiceStyle}. Speaking speed: ${input.audioSpeed ?? "1×"}. Timing basis: ${input.timingBasis ?? "Audio duration"}. Target platform: ${input.platform}. ${input.durationHint ?? "Keep it concise."}` }] });
      const content = response.choices?.[0]?.message?.content;
      return { script: typeof content === "string" ? content : "AI returned no narration.", mode: "server-ai" as const };
    }),
  }),
  export: router({
    prepare: publicProcedure.input(exportPayloadInput.extend({ requestedFormat: z.enum(["MP4", "WAV", "SRT"]) })).mutation(async ({ input }) => ({ accepted: true as const, format: input.requestedFormat, ready: input.requestedFormat !== "WAV" || Boolean(process.env.BUILT_IN_FORGE_API_KEY), formats: ["MP4", "WAV", "SRT"] as const, payload: input, outputUrl: null as string | null, note: input.requestedFormat === "WAV" && !process.env.BUILT_IN_FORGE_API_KEY ? "Voiceover requires server AI configuration." : "Export manifest validated." })),
  }),
  settings: router({
    get: publicProcedure.query(async () => getAppSettings()),
    update: adminProcedure.input(settingsInput).mutation(async ({ input }) => saveAppSettings(input)),
  }),
});
export type AppRouter = typeof appRouter;
