import { mkdir } from "node:fs/promises";
import path from "node:path";
import { runFfmpeg } from "./compose.ts";
import { logger } from "./logger.ts";
import { canvasSize, type AspectRatio, type VideoResolution } from "./types.ts";

export const CTA_PAD_COLOR = "0xF7F4EE";

export async function writeCtaCanvas(opts: {
  sourceImagePath: string;
  aspectRatio: AspectRatio;
  outputPath: string;
  resolution?: VideoResolution;
}): Promise<string> {
  const { width, height } = canvasSize(opts.aspectRatio, opts.resolution ?? "720p");
  await mkdir(path.dirname(opts.outputPath), { recursive: true });
  const vf = `scale=${width}:${height}:force_original_aspect_ratio=decrease,pad=${width}:${height}:(ow-iw)/2:(oh-ih)/2:color=${CTA_PAD_COLOR},setsar=1`;
  await runFfmpeg(["-y", "-i", opts.sourceImagePath, "-vf", vf, opts.outputPath]);
  logger.info("Wrote CTA canvas", { aspectRatio: opts.aspectRatio, outputPath: opts.outputPath });
  return opts.outputPath;
}

export async function writeAllCtaCanvases(
  sourceImagePath: string,
  outputDir: string,
  resolution: VideoResolution = "720p",
): Promise<Record<AspectRatio, string>> {
  await mkdir(outputDir, { recursive: true });
  const ratios: AspectRatio[] = ["9:16", "1:1", "16:9"];
  const result = {} as Record<AspectRatio, string>;
  for (const aspectRatio of ratios) {
    const token = aspectRatio.replace(":", "x");
    const outputPath = path.join(outputDir, `cta-${token}.png`);
    result[aspectRatio] = await writeCtaCanvas({
      sourceImagePath,
      aspectRatio,
      outputPath,
      resolution,
    });
  }
  return result;
}
