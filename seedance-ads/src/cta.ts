import { mkdir, readFile, rename, writeFile } from "node:fs/promises";
import path from "node:path";
import { runFfmpeg, runFfprobe } from "./compose.ts";
import {
  CTA_LOCKUP_CROP,
  CTA_MASTER_SIZE,
  CTA_PAD_COLOR,
} from "./ctaCopy.ts";
import { buildCtaHtml, resolveChromePath, screenshotHtml } from "./ctaLayout.ts";
import { logger } from "./logger.ts";
import { canvasSize, type AspectRatio, type VideoResolution } from "./types.ts";

export { CTA_BACKGROUND, CTA_COPY, CTA_COPY_STRINGS, CTA_PAD_COLOR } from "./ctaCopy.ts";

export type CtaLayout = "contain" | "native";

async function probeImageSize(filePath: string): Promise<{ width: number; height: number }> {
  const raw = await runFfprobe([
    "-v",
    "error",
    "-select_streams",
    "v:0",
    "-show_entries",
    "stream=width,height",
    "-of",
    "csv=p=0:s=x",
    filePath,
  ]);
  const [width, height] = raw.split("x").map((part) => Number(part));
  if (!width || !height) {
    throw new Error(`Could not read image size from ${filePath}: ${raw}`);
  }
  return { width, height };
}

export async function cropCtaLockup(sourceImagePath: string, outputPath: string): Promise<string> {
  const size = await probeImageSize(sourceImagePath);
  const scaleX = size.width / CTA_MASTER_SIZE.width;
  const scaleY = size.height / CTA_MASTER_SIZE.height;
  const x = Math.round(CTA_LOCKUP_CROP.x * scaleX);
  const y = Math.round(CTA_LOCKUP_CROP.y * scaleY);
  const width = Math.round(CTA_LOCKUP_CROP.width * scaleX);
  const height = Math.round(CTA_LOCKUP_CROP.height * scaleY);
  await mkdir(path.dirname(outputPath), { recursive: true });
  await runFfmpeg([
    "-y",
    "-i",
    sourceImagePath,
    "-frames:v",
    "1",
    "-update",
    "1",
    "-vf",
    `crop=${width}:${height}:${x}:${y}`,
    outputPath,
  ]);
  return outputPath;
}

async function fitPngToCanvas(
  filePath: string,
  width: number,
  height: number,
): Promise<void> {
  const size = await probeImageSize(filePath);
  if (size.width === width && size.height === height) return;
  const tmpPath = `${filePath}.fit.png`;
  const vf = `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=${CTA_PAD_COLOR},setsar=1`;
  await runFfmpeg([
    "-y",
    "-i",
    filePath,
    "-frames:v",
    "1",
    "-update",
    "1",
    "-vf",
    vf,
    tmpPath,
  ]);
  await rename(tmpPath, filePath);
}

/**
 * Letterbox the 9:16 Shopify master onto the target canvas.
 * Text is never redrawn — the original pixels are only scaled uniformly.
 */
export async function writeCtaCanvas(opts: {
  sourceImagePath: string;
  aspectRatio: AspectRatio;
  outputPath: string;
  resolution?: VideoResolution;
}): Promise<string> {
  const { width, height } = canvasSize(opts.aspectRatio, opts.resolution ?? "720p");
  await mkdir(path.dirname(opts.outputPath), { recursive: true });
  const vf = `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=${CTA_PAD_COLOR},setsar=1`;
  await runFfmpeg([
    "-y",
    "-i",
    opts.sourceImagePath,
    "-frames:v",
    "1",
    "-update",
    "1",
    "-vf",
    vf,
    opts.outputPath,
  ]);
  logger.info("Wrote CTA canvas", {
    aspectRatio: opts.aspectRatio,
    outputPath: opts.outputPath,
    layout: "contain",
  });
  return opts.outputPath;
}

async function writeNativeCtaCanvas(opts: {
  sourceImagePath: string;
  lockupDataUri: string;
  chromePath: string;
  aspectRatio: AspectRatio;
  outputPath: string;
  workDir: string;
  resolution?: VideoResolution;
}): Promise<string> {
  const { width, height } = canvasSize(opts.aspectRatio, opts.resolution ?? "720p");
  await mkdir(path.dirname(opts.outputPath), { recursive: true });

  if (opts.aspectRatio === "9:16") {
    return writeCtaCanvas({
      sourceImagePath: opts.sourceImagePath,
      aspectRatio: opts.aspectRatio,
      outputPath: opts.outputPath,
      resolution: opts.resolution,
    });
  }

  const html = buildCtaHtml({
    aspectRatio: opts.aspectRatio,
    lockupDataUri: opts.lockupDataUri,
    width,
    height,
  });
  const htmlPath = path.join(opts.workDir, `cta-${opts.aspectRatio.replace(":", "x")}.html`);
  await writeFile(htmlPath, html, "utf8");
  await screenshotHtml({
    htmlPath,
    outputPath: opts.outputPath,
    width,
    height,
    chromePath: opts.chromePath,
  });
  await fitPngToCanvas(opts.outputPath, width, height);
  logger.info("Wrote CTA canvas", {
    aspectRatio: opts.aspectRatio,
    outputPath: opts.outputPath,
    layout: "native",
  });
  return opts.outputPath;
}

export async function writeAllCtaCanvases(
  sourceImagePath: string,
  outputDir: string,
  resolution: VideoResolution = "720p",
  layout: CtaLayout = "native",
): Promise<Record<AspectRatio, string>> {
  await mkdir(outputDir, { recursive: true });
  const ratios: AspectRatio[] = ["9:16", "1:1", "16:9"];
  const result = {} as Record<AspectRatio, string>;

  let native = layout === "native";
  let chromePath: string | null = null;
  let lockupDataUri = "";
  const workDir = path.join(outputDir, "_native");

  if (native) {
    chromePath = await resolveChromePath();
    if (!chromePath) {
      logger.info("Chrome not found; falling back to contain CTA canvases");
      native = false;
    } else {
      await mkdir(workDir, { recursive: true });
      const lockupPath = path.join(workDir, "lockup.png");
      await cropCtaLockup(sourceImagePath, lockupPath);
      lockupDataUri = `data:image/png;base64,${(await readFile(lockupPath)).toString("base64")}`;
    }
  }

  for (const aspectRatio of ratios) {
    const token = aspectRatio.replace(":", "x");
    const outputPath = path.join(outputDir, `cta-${token}.png`);
    if (native && chromePath) {
      result[aspectRatio] = await writeNativeCtaCanvas({
        sourceImagePath,
        lockupDataUri,
        chromePath,
        aspectRatio,
        outputPath,
        workDir,
        resolution,
      });
    } else {
      result[aspectRatio] = await writeCtaCanvas({
        sourceImagePath,
        aspectRatio,
        outputPath,
        resolution,
      });
    }
  }
  return result;
}
