export type StoragePolicy = "session" | "retained";
export type ThemeDirection = "violet-teal" | "indigo-rose";

export type MovieRecapConfig = {
  brandName: string;
  theme: ThemeDirection;
  uploadLimitMb: number;
  storagePolicy: StoragePolicy;
  defaultPlatform: "YouTube" | "TikTok" | "Facebook";
  enabledTools: string[];
  exportFormats: Array<"MP4" | "WAV" | "SRT">;
};

export const DEFAULT_MOVIE_RECAP_CONFIG: MovieRecapConfig = {
  brandName: "AungMin Movie Recap",
  theme: "violet-teal",
  uploadLimitMb: 200,
  storagePolicy: "session",
  defaultPlatform: "YouTube",
  enabledTools: ["script", "voice", "subtitle", "blur", "overlays", "export"],
  exportFormats: ["MP4", "WAV", "SRT"],
};

export function isUploadWithinLimit(sizeBytes: number, limitMb: number): boolean {
  return Number.isFinite(sizeBytes) && sizeBytes >= 0 && Number.isFinite(limitMb) && sizeBytes <= limitMb * 1024 * 1024;
}

export function normalizeMovieRecapConfig(input: Partial<MovieRecapConfig> = {}): MovieRecapConfig {
  const brandName = typeof input.brandName === "string" && input.brandName.trim() ? input.brandName.trim().slice(0, 120) : DEFAULT_MOVIE_RECAP_CONFIG.brandName;
  const uploadLimitMb = typeof input.uploadLimitMb === "number" && Number.isFinite(input.uploadLimitMb) && input.uploadLimitMb >= 10 ? Math.min(2048, Math.round(input.uploadLimitMb)) : DEFAULT_MOVIE_RECAP_CONFIG.uploadLimitMb;
  const enabledTools = Array.isArray(input.enabledTools) ? input.enabledTools.filter((tool): tool is string => typeof tool === "string" && DEFAULT_MOVIE_RECAP_CONFIG.enabledTools.includes(tool)) : DEFAULT_MOVIE_RECAP_CONFIG.enabledTools;
  const defaultPlatform = ["YouTube", "TikTok", "Facebook"].includes(input.defaultPlatform ?? "") ? input.defaultPlatform as MovieRecapConfig["defaultPlatform"] : DEFAULT_MOVIE_RECAP_CONFIG.defaultPlatform;
  const exportFormats = Array.isArray(input.exportFormats) ? input.exportFormats.filter((format): format is "MP4" | "WAV" | "SRT" => ["MP4", "WAV", "SRT"].includes(format)) : DEFAULT_MOVIE_RECAP_CONFIG.exportFormats;
  return {
    brandName,
    theme: input.theme === "indigo-rose" ? "indigo-rose" : DEFAULT_MOVIE_RECAP_CONFIG.theme,
    uploadLimitMb,
    storagePolicy: input.storagePolicy === "retained" ? "retained" : DEFAULT_MOVIE_RECAP_CONFIG.storagePolicy,
    defaultPlatform,
    enabledTools: enabledTools.length ? Array.from(new Set(enabledTools)) : DEFAULT_MOVIE_RECAP_CONFIG.enabledTools,
    exportFormats: exportFormats.length ? Array.from(new Set(exportFormats)) : DEFAULT_MOVIE_RECAP_CONFIG.exportFormats,
  };
}
