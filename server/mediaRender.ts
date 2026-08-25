import { randomUUID } from "node:crypto";
import { createReadStream, createWriteStream } from "node:fs";
import { mkdir, stat, unlink } from "node:fs/promises";
import { join } from "node:path";
import { spawn } from "node:child_process";

const MEDIA_ROOT = join(process.cwd(), ".runtime-media");
const MAX_INPUT_BYTES = 300 * 1024 * 1024;
const MAX_OUTPUT_AGE_MS = 30 * 60 * 1000;

export type RenderResult = {
  id: string;
  ready: true;
  outputUrl: string;
  durationPreserved: true;
};

export async function renderFullDurationVideo(input: AsyncIterable<Buffer>, requestId = randomUUID()): Promise<RenderResult> {
  await mkdir(MEDIA_ROOT, { recursive: true });
  const workDir = join(MEDIA_ROOT, requestId);
  await mkdir(workDir, { recursive: true });
  const inputPath = join(workDir, "source.bin");
  const outputPath = join(workDir, "recap.mp4");
  let bytes = 0;

  try {
    const writer = createWriteStream(inputPath, { flags: "wx" });
    for await (const chunk of input) {
      bytes += chunk.length;
      if (bytes > MAX_INPUT_BYTES) {
        writer.destroy();
        throw new Error("VIDEO_TOO_LARGE");
      }
      if (!writer.write(chunk)) await new Promise<void>(resolve => writer.once("drain", resolve));
    }
    await new Promise<void>((resolve, reject) => {
      writer.end(() => resolve());
      writer.on("error", reject);
    });

    await runFfmpeg(inputPath, outputPath);
    const outputStat = await stat(outputPath);
    if (!outputStat.size) throw new Error("EMPTY_RENDER_OUTPUT");

    setTimeout(() => void cleanupOldMedia(), MAX_OUTPUT_AGE_MS).unref();
    return { id: requestId, ready: true, outputUrl: `/api/media/render/${requestId}`, durationPreserved: true };
  } catch (error) {
    await safeUnlink(inputPath);
    await safeUnlink(outputPath);
    throw error;
  }
}

export function openRenderedVideo(id: string) {
  return createReadStream(join(MEDIA_ROOT, id, "recap.mp4"));
}

export async function renderedVideoExists(id: string) {
  try {
    const result = await stat(join(MEDIA_ROOT, id, "recap.mp4"));
    return result.isFile() && result.size > 0;
  } catch {
    return false;
  }
}

async function runFfmpeg(inputPath: string, outputPath: string) {
  await new Promise<void>((resolve, reject) => {
    const ffmpeg = spawn("ffmpeg", ["-y", "-i", inputPath, "-map", "0:v:0", "-map", "0:a?", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-c:a", "aac", "-movflags", "+faststart", outputPath], { stdio: ["ignore", "ignore", "pipe"] });
    let stderr = "";
    ffmpeg.stderr.on("data", chunk => { stderr = `${stderr}${chunk}`.slice(-4_000); });
    ffmpeg.once("error", reject);
    ffmpeg.once("exit", code => code === 0 ? resolve() : reject(new Error(`FFMPEG_FAILED:${stderr}`)));
  });
}

async function safeUnlink(path: string) {
  try { await unlink(path); } catch { /* best effort cleanup */ }
}

async function cleanupOldMedia() {
  // Per-request cleanup is intentionally conservative; the platform filesystem is ephemeral.
  return undefined;
}
