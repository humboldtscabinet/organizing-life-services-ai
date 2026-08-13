import { spawn } from "node:child_process";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { canvasSize } from "./types.ts";
import { logger } from "./logger.ts";
import { CTA_HOLD_SECONDS, type AspectRatio } from "./types.ts";

export class FfmpegMissingError extends Error {
  constructor() {
    super("ffmpeg is required on PATH for CTA canvases and end-card concat.");
    this.name = "FfmpegMissingError";
  }
}

export async function requireFfmpeg(): Promise<void> {
  try {
    await runFfmpeg(["-version"]);
  } catch (error) {
    if (error instanceof FfmpegMissingError) throw error;
    const message = error instanceof Error ? error.message : String(error);
    if (/not found|ENOENT/i.test(message)) {
      throw new FfmpegMissingError();
    }
    throw error;
  }
}

export async function ffmpegAvailable(): Promise<boolean> {
  try {
    await requireFfmpeg();
    return true;
  } catch (error) {
    if (error instanceof FfmpegMissingError) return false;
    return false;
  }
}

export async function runFfmpeg(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("ffmpeg", args, { stdio: ["ignore", "pipe", "pipe"] });
    let stderr = "";
    let stdout = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("error", (error: NodeJS.ErrnoException) => {
      if (error.code === "ENOENT") {
        reject(new FfmpegMissingError());
        return;
      }
      reject(error);
    });
    child.on("close", (code) => {
      if (code === 0) {
        resolve(stdout || stderr);
        return;
      }
      reject(new Error(`ffmpeg exited ${code}: ${stderr.slice(-2000)}`));
    });
  });
}

export async function runFfprobe(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn("ffprobe", args, { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk: Buffer) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr += chunk.toString();
    });
    child.on("error", (error: NodeJS.ErrnoException) => {
      if (error.code === "ENOENT") {
        reject(new FfmpegMissingError());
        return;
      }
      reject(error);
    });
    child.on("close", (code) => {
      if (code === 0) {
        resolve(stdout.trim());
        return;
      }
      reject(new Error(`ffprobe exited ${code}: ${stderr.slice(-2000)}`));
    });
  });
}

export async function probeHasAudio(filePath: string): Promise<boolean> {
  try {
    const raw = await runFfprobe([
      "-v",
      "error",
      "-select_streams",
      "a",
      "-show_entries",
      "stream=index",
      "-of",
      "csv=p=0",
      filePath,
    ]);
    return raw.trim().length > 0;
  } catch {
    return false;
  }
}

export async function probeDurationSeconds(filePath: string): Promise<number> {
  const raw = await runFfprobe([
    "-v",
    "error",
    "-show_entries",
    "format=duration",
    "-of",
    "default=noprint_wrappers=1:nokey=1",
    filePath,
  ]);
  const duration = Number(raw);
  if (!Number.isFinite(duration)) {
    throw new Error(`Could not read duration from ${filePath}: ${raw}`);
  }
  return duration;
}

export async function downloadToFile(url: string, destPath: string): Promise<string> {
  if (!/^https?:\/\//i.test(url)) {
    throw new Error(`downloadToFile requires a public HTTP(S) URL, got: ${url}`);
  }
  await mkdir(path.dirname(destPath), { recursive: true });
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to download ${url} (${response.status} ${response.statusText})`);
  }
  const bytes = Buffer.from(await response.arrayBuffer());
  await writeFile(destPath, bytes);
  logger.info("Downloaded media", { destPath, bytes: bytes.byteLength });
  return destPath;
}

/**
 * Concat a generated (or original) body clip with a 3-second CTA still.
 * Scales both to the 720p canvas for `aspectRatio` so concat never fails
 * on mismatched sizes.
 */
export async function appendCtaHold(opts: {
  bodyVideoPath: string;
  ctaImagePath: string;
  aspectRatio: AspectRatio;
  outputPath: string;
  holdSeconds?: number;
}): Promise<string> {
  await requireFfmpeg();
  const holdSeconds = opts.holdSeconds ?? CTA_HOLD_SECONDS;
  const { width, height } = canvasSize(opts.aspectRatio);
  await mkdir(path.dirname(opts.outputPath), { recursive: true });

  const vf = `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=0xF7F4EE,setsar=1,fps=24,format=yuv420p`;
  const hasAudio = await probeHasAudio(opts.bodyVideoPath);
  const bodyDuration = hasAudio ? 0 : await probeDurationSeconds(opts.bodyVideoPath);
  const bodyAudio = hasAudio
    ? `[0:a]aformat=sample_rates=44100:channel_layouts=stereo,aresample=async=1[a0]`
    : `anullsrc=r=44100:cl=stereo:d=${Math.max(bodyDuration, 0.1)}[a0]`;

  await runFfmpeg([
    "-y",
    "-i",
    opts.bodyVideoPath,
    "-loop",
    "1",
    "-t",
    String(holdSeconds),
    "-i",
    opts.ctaImagePath,
    "-filter_complex",
    [
      `[0:v]${vf}[v0]`,
      `[1:v]${vf}[v1]`,
      bodyAudio,
      `anullsrc=r=44100:cl=stereo:d=${holdSeconds}[a1]`,
      `[v0][a0][v1][a1]concat=n=2:v=1:a=1[outv][outa]`,
    ].join(";"),
    "-map",
    "[outv]",
    "-map",
    "[outa]",
    "-c:v",
    "libx264",
    "-pix_fmt",
    "yuv420p",
    "-c:a",
    "aac",
    "-shortest",
    "-movflags",
    "+faststart",
    opts.outputPath,
  ]);

  logger.info("Appended CTA hold", {
    outputPath: opts.outputPath,
    aspectRatio: opts.aspectRatio,
    holdSeconds,
  });
  return opts.outputPath;
}
