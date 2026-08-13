import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { createByteDance } from "@ai-sdk/bytedance";
import {
  experimental_generateVideo as generateVideo,
  NoVideoGeneratedError,
} from "ai";
import { config as loadEnv } from "dotenv";
import { buildPrompt, hasFramingRule } from "./framing.ts";
import { logger } from "./logger.ts";
import {
  ASPECT_RATIOS,
  DEFAULT_DURATION_SECONDS,
  DEFAULT_RESOLUTION,
  DEFAULT_SEEDANCE_MODEL,
  PIXEL_RESOLUTION,
  generateAdOptionsSchema,
  type AspectRatio,
  type GenerateAdOptions,
  type GenerateAdResult,
  type GenerateAllRatiosResult,
  type ParsedGenerateAdOptions,
  type PreparedGeneration,
  type SeedanceClientConfig,
  type VideoResolution,
} from "./types.ts";

loadEnv({ quiet: true });

const DEFAULT_POLL_INTERVAL_MS = 5_000;
const DEFAULT_POLL_TIMEOUT_MS = 15 * 60 * 1000;
const DEFAULT_OUTPUT_DIR = "output";

const IMAGE_MIME: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".gif": "image/gif",
};

function isHttpOrDataUri(value: string): boolean {
  return /^(https?:\/\/|data:)/i.test(value);
}

function isSeedance2(model: string): boolean {
  return /seedance-2/i.test(model);
}

function clampResolution(model: string, requested: VideoResolution): {
  resolution: VideoResolution;
  warning?: string;
} {
  if (requested === "1080p" && isSeedance2(model)) {
    return {
      resolution: "720p",
      warning:
        "Seedance 2.0 supports 480p and 720p only. Requested 1080p was clamped to 720p.",
    };
  }
  return { resolution: requested };
}

/**
 * Single pipeline used by every generation path.
 * Framing is injected here so text-to-video, image-to-video, and
 * generateAllRatios() cannot skip it.
 */
export function prepareGeneration(
  options: ParsedGenerateAdOptions,
  model: string,
): PreparedGeneration {
  const aspectRatio = options.aspectRatio;
  const framedPrompt = buildPrompt(options.prompt, aspectRatio);

  if (!hasFramingRule(framedPrompt, aspectRatio)) {
    throw new Error(
      `Internal error: framing rule for ${aspectRatio} was not applied.`,
    );
  }

  const { resolution, warning: resolutionWarning } = clampResolution(
    model,
    options.resolution,
  );
  const pixelResolution = PIXEL_RESOLUTION[resolution][aspectRatio];
  const mode = options.image ? "image-to-video" : "text-to-video";
  const warnings: string[] = [];

  if (resolutionWarning) {
    warnings.push(resolutionWarning);
  }

  // Newer Seedance models inherit ratio from first-frame / first-last-frame
  // media and reject an explicit aspectRatio on those paths.
  let sdkAspectRatio: AspectRatio | "adaptive" = aspectRatio;
  if (mode === "image-to-video") {
    sdkAspectRatio = "adaptive";
    warnings.push(
      `Image-to-video inherits the source image ratio on Seedance 2.x. ` +
        `Framing for ${aspectRatio} was still appended — provide a ${aspectRatio} source image (and CTA card) for Performance Max.`,
    );
  }

  return {
    aspectRatio,
    framedPrompt,
    duration: options.duration,
    resolution,
    pixelResolution,
    mode,
    warnings,
    sdkAspectRatio,
  };
}

function ratioFileToken(ratio: AspectRatio): string {
  return ratio.replace(":", "x");
}

function defaultFileName(aspectRatio: AspectRatio): string {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `ad-${stamp}-${ratioFileToken(aspectRatio)}.mp4`;
}

function warningText(warning: unknown): string {
  if (typeof warning === "string") return warning;
  if (warning && typeof warning === "object") {
    const record = warning as Record<string, unknown>;
    return (
      String(record.message ?? record.details ?? record.feature ?? "") ||
      JSON.stringify(warning)
    );
  }
  return String(warning);
}

function extractTaskId(metadata: unknown): string | undefined {
  if (!metadata || typeof metadata !== "object") return undefined;
  const bytedance = (metadata as Record<string, unknown>).bytedance;
  if (!bytedance || typeof bytedance !== "object") return undefined;
  const taskId = (bytedance as Record<string, unknown>).taskId;
  return typeof taskId === "string" ? taskId : undefined;
}

export class SeedanceClient {
  private readonly apiKey: string;
  private readonly model: string;
  private readonly baseURL: string | undefined;
  private readonly pollIntervalMs: number;
  private readonly pollTimeoutMs: number;

  constructor(config: SeedanceClientConfig = {}) {
    const apiKey = config.apiKey ?? process.env.ARK_API_KEY;
    if (!apiKey) {
      throw new Error(
        "Missing ARK_API_KEY. Copy seedance-ads/.env.example to .env and add your BytePlus ModelArk key.",
      );
    }

    this.apiKey = apiKey;
    this.model = config.model ?? process.env.SEEDANCE_MODEL ?? DEFAULT_SEEDANCE_MODEL;
    this.baseURL = config.baseURL;
    this.pollIntervalMs = config.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
    this.pollTimeoutMs = config.pollTimeoutMs ?? DEFAULT_POLL_TIMEOUT_MS;
  }

  getModel(): string {
    return this.model;
  }

  /**
   * Generate one ad creative. Framing for `options.aspectRatio` is
   * appended automatically — callers pass only the creative brief.
   */
  async generate(rawOptions: GenerateAdOptions): Promise<GenerateAdResult> {
    const options = generateAdOptionsSchema.parse(rawOptions);
    const prepared = prepareGeneration(options, this.model);
    const started = Date.now();

    logger.info("Starting Seedance generation", {
      model: this.model,
      aspectRatio: prepared.aspectRatio,
      duration: prepared.duration,
      mode: prepared.mode,
      resolution: prepared.pixelResolution,
      framingApplied: hasFramingRule(prepared.framedPrompt, prepared.aspectRatio),
    });

    for (const warning of prepared.warnings) {
      logger.warn(warning);
    }

    const byteDance = createByteDance({
      apiKey: this.apiKey,
      ...(this.baseURL ? { baseURL: this.baseURL } : {}),
    });

    const bytedanceOptions: {
      watermark: boolean;
      cameraFixed?: boolean;
      generateAudio?: boolean;
      lastFrameImage?: string;
      referenceImages?: string[];
      referenceVideos?: string[];
      referenceAudio?: string[];
    } = {
      watermark: options.watermark,
    };

    if (options.cameraFixed != null) {
      bytedanceOptions.cameraFixed = options.cameraFixed;
    }
    if (options.generateAudio != null) {
      bytedanceOptions.generateAudio = options.generateAudio;
    }
    if (options.lastFrameImage) {
      bytedanceOptions.lastFrameImage = await this.resolveUrlOrDataUri(
        options.lastFrameImage,
      );
    }
    if (options.referenceImages?.length) {
      bytedanceOptions.referenceImages = options.referenceImages;
    }
    if (options.referenceVideos?.length) {
      bytedanceOptions.referenceVideos = options.referenceVideos;
    }
    if (options.referenceAudio?.length) {
      bytedanceOptions.referenceAudio = options.referenceAudio;
    }

    const prompt = options.image
      ? {
          text: prepared.framedPrompt,
          image: await this.resolveMedia(options.image),
        }
      : prepared.framedPrompt;

    try {
      const { video, warnings: sdkWarnings, providerMetadata } = await generateVideo({
        model: byteDance.video(this.model),
        prompt,
        aspectRatio: prepared.sdkAspectRatio,
        duration: prepared.duration,
        resolution: prepared.pixelResolution,
        seed: options.seed,
        generateAudio: options.generateAudio,
        poll: {
          intervalMs: this.pollIntervalMs,
          timeoutMs: this.pollTimeoutMs,
        },
        providerOptions: {
          bytedance: bytedanceOptions,
        },
      });

      const resultWarnings = [
        ...prepared.warnings,
        ...(sdkWarnings ?? []).map(warningText).filter(Boolean),
      ];

      const taskId = extractTaskId(providerMetadata);
      let videoPath: string | undefined;

      if (!options.skipDownload) {
        const outputDir = options.outputDir ?? DEFAULT_OUTPUT_DIR;
        videoPath = await this.persistVideo(
          video,
          outputDir,
          defaultFileName(prepared.aspectRatio),
        );
      }

      const result: GenerateAdResult = {
        aspectRatio: prepared.aspectRatio,
        prompt: options.prompt,
        framedPrompt: prepared.framedPrompt,
        duration: prepared.duration,
        model: this.model,
        resolution: prepared.resolution,
        pixelResolution: prepared.pixelResolution,
        mode: prepared.mode,
        videoPath,
        taskId,
        warnings: resultWarnings,
        elapsedMs: Date.now() - started,
      };

      logger.info("Seedance generation complete", {
        aspectRatio: result.aspectRatio,
        elapsedMs: result.elapsedMs,
        videoPath: result.videoPath,
        taskId: result.taskId,
      });

      return result;
    } catch (error) {
      const elapsedMs = Date.now() - started;
      if (NoVideoGeneratedError.isInstance(error)) {
        logger.error("Seedance returned no video", {
          aspectRatio: prepared.aspectRatio,
          elapsedMs,
          cause: error.cause,
        });
        throw new Error(
          `Seedance generated no video for ${prepared.aspectRatio} (${elapsedMs}ms): ${String(error.cause ?? error.message)}`,
          { cause: error },
        );
      }

      const message = error instanceof Error ? error.message : String(error);
      logger.error("Seedance generation failed", {
        aspectRatio: prepared.aspectRatio,
        elapsedMs,
        error: message,
      });
      throw new Error(
        `Seedance generation failed for ${prepared.aspectRatio}: ${message}`,
        { cause: error },
      );
    }
  }

  /**
   * Produce the full Performance Max set: 9:16, 1:1, and 16:9.
   * Each call independently injects that ratio's framing rule.
   */
  async generateAllRatios(
    rawOptions: Omit<GenerateAdOptions, "aspectRatio">,
    opts: { parallel?: boolean } = {},
  ): Promise<GenerateAllRatiosResult> {
    logger.info("Generating full Performance Max ad set", {
      ratios: ASPECT_RATIOS.join(", "),
      parallel: Boolean(opts.parallel),
    });

    const results: GenerateAdResult[] = [];
    const failures: GenerateAllRatiosResult["failures"] = [];

    const runOne = async (aspectRatio: AspectRatio) => {
      try {
        const result = await this.generate({ ...rawOptions, aspectRatio });
        results.push(result);
      } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        failures.push({ aspectRatio, error: message });
      }
    };

    if (opts.parallel) {
      await Promise.all(ASPECT_RATIOS.map((ratio) => runOne(ratio)));
    } else {
      for (const ratio of ASPECT_RATIOS) {
        await runOne(ratio);
      }
    }

    logger.info("Full ad set finished", {
      succeeded: results.length,
      failed: failures.length,
    });

    return { results, failures };
  }

  private async resolveMedia(source: string): Promise<string | Uint8Array> {
    if (isHttpOrDataUri(source)) {
      return source;
    }

    const buffer = await readFile(source);
    logger.info("Loaded local media file", { source, bytes: buffer.byteLength });
    return new Uint8Array(buffer);
  }

  private async resolveUrlOrDataUri(source: string): Promise<string> {
    if (isHttpOrDataUri(source)) {
      return source;
    }

    const buffer = await readFile(source);
    const mime = IMAGE_MIME[path.extname(source).toLowerCase()] ?? "image/png";
    logger.info("Encoded local image as data URI", {
      source,
      bytes: buffer.byteLength,
      mime,
    });
    return `data:${mime};base64,${buffer.toString("base64")}`;
  }

  private async persistVideo(
    video: { uint8Array?: Uint8Array; base64?: string; url?: string },
    outputDir: string,
    fileName: string,
  ): Promise<string> {
    await mkdir(outputDir, { recursive: true });
    const outputPath = path.resolve(outputDir, fileName);

    if (video.uint8Array && video.uint8Array.byteLength > 0) {
      await writeFile(outputPath, video.uint8Array);
      logger.info("Wrote video from bytes", { outputPath, bytes: video.uint8Array.byteLength });
      return outputPath;
    }

    if (video.base64) {
      const bytes = Buffer.from(video.base64, "base64");
      await writeFile(outputPath, bytes);
      logger.info("Wrote video from base64", { outputPath, bytes: bytes.byteLength });
      return outputPath;
    }

    if (video.url) {
      const response = await fetch(video.url);
      if (!response.ok) {
        throw new Error(
          `Failed to download generated video (${response.status} ${response.statusText})`,
        );
      }
      const bytes = Buffer.from(await response.arrayBuffer());
      await writeFile(outputPath, bytes);
      logger.info("Downloaded video from ModelArk URL", {
        outputPath,
        bytes: bytes.byteLength,
      });
      return outputPath;
    }

    throw new Error("Seedance returned a video object with no bytes, base64, or URL.");
  }
}

/** Convenience re-export so tests can assert defaults without constructing a client. */
export const clientDefaults = {
  model: DEFAULT_SEEDANCE_MODEL,
  duration: DEFAULT_DURATION_SECONDS,
  resolution: DEFAULT_RESOLUTION,
  outputDir: DEFAULT_OUTPUT_DIR,
};
