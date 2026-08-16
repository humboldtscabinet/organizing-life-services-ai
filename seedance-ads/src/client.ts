import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { createByteDance } from "@ai-sdk/bytedance";
import {
  experimental_generateVideo as generateVideo,
  NoVideoGeneratedError,
} from "ai";
import { config as loadEnv } from "dotenv";
import { appendReferenceGuidance, TEXT_TO_VIDEO_ACCURACY_WARNING } from "./brand.ts";
import { buildPrompt, hasFramingRule } from "./framing.ts";
import { logger } from "./logger.ts";
import {
  DEFAULT_SEEVIO_MODEL,
  SEEVIO_BASE_URL,
  SeevioApi,
  buildSeevioPayload,
} from "./seevio.ts";
import {
  ASPECT_RATIOS,
  DEFAULT_DURATION_SECONDS,
  DEFAULT_RESOLUTION,
  PIXEL_RESOLUTION,
  generateAdOptionsSchema,
  type AspectRatio,
  type GenerateAdOptions,
  type GenerateAdResult,
  type GenerateAllRatiosResult,
  type ParsedGenerateAdOptions,
  type PreparedGeneration,
  type SeedanceClientConfig,
  type SeedanceProvider,
  type VideoResolution,
} from "./types.ts";

loadEnv({ quiet: true });

const DEFAULT_POLL_INTERVAL_MS = 10_000;
const DEFAULT_POLL_TIMEOUT_MS = 15 * 60 * 1000;
const DEFAULT_OUTPUT_DIR = "output";

function resolveApiKey(config: SeedanceClientConfig, provider: SeedanceProvider): string {
  if (config.apiKey) return config.apiKey;

  if (provider === "seevio") {
    const key =
      process.env.SEEDANCE_API_KEY ??
      process.env.SEEVIO_API_KEY ??
      process.env.ARK_API_KEY;
    if (!key) {
      throw new Error(
        "Missing SEEDANCE_API_KEY. Add your Seevio (seedance2.ai) sk_live_ key as a Cursor Runtime Secret named SEEDANCE_API_KEY, then restart this agent.",
      );
    }
    return key;
  }

  const key = process.env.ARK_API_KEY;
  if (!key) {
    throw new Error(
      "Missing ARK_API_KEY. BytePlus ModelArk requires this env var.",
    );
  }
  return key;
}

function resolveProvider(config: SeedanceClientConfig): SeedanceProvider {
  const raw = config.provider ?? process.env.SEEDANCE_PROVIDER ?? "seevio";
  if (raw === "seevio" || raw === "bytedance") return raw;
  throw new Error(`Unknown SEEDANCE_PROVIDER "${raw}". Use seevio or bytedance.`);
}

function isSeedance25(model: string): boolean {
  return /2-5|2\.5/.test(model);
}

function clampResolution(model: string, requested: VideoResolution): {
  resolution: VideoResolution;
  warning?: string;
} {
  // Seevio Seedance 2.5 and BytePlus ModelArk Seedance 2.0 are 720p-max.
  if (requested === "1080p" && (isSeedance25(model) || /dreamina-seedance-2-0/.test(model))) {
    return {
      resolution: "720p",
      warning: `${model} supports 480p and 720p only. Requested 1080p was clamped to 720p.`,
    };
  }
  return { resolution: requested };
}

function clampDuration(model: string, duration: number): {
  duration: number;
  warning?: string;
} {
  const max = isSeedance25(model) ? 30 : 15;
  if (duration > max) {
    return {
      duration: max,
      warning: `${model} max duration is ${max}s. Requested ${duration}s was clamped.`,
    };
  }
  return { duration };
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
  const hasReferences = Boolean(
    options.referenceImages?.length ||
      options.referenceVideos?.length ||
      options.referenceAudio?.length,
  );
  const guidedPrompt = appendReferenceGuidance(
    options.prompt,
    options.referenceImages?.length ?? 0,
  );
  const framedPrompt = buildPrompt(guidedPrompt, aspectRatio, {
    hasCtaCard: Boolean(options.lastFrameImage),
  });

  if (!hasFramingRule(framedPrompt, aspectRatio)) {
    throw new Error(
      `Internal error: framing rule for ${aspectRatio} was not applied.`,
    );
  }

  const { resolution, warning: resolutionWarning } = clampResolution(
    model,
    options.resolution,
  );
  const { duration, warning: durationWarning } = clampDuration(model, options.duration);
  const pixelResolution = PIXEL_RESOLUTION[resolution][aspectRatio];
  const mode = options.image
    ? "image-to-video"
    : hasReferences
      ? "reference-to-video"
      : "text-to-video";
  const warnings: string[] = [];

  if (resolutionWarning) warnings.push(resolutionWarning);
  if (durationWarning) warnings.push(durationWarning);
  if (mode === "text-to-video") {
    warnings.push(TEXT_TO_VIDEO_ACCURACY_WARNING);
  }

  let sdkAspectRatio: AspectRatio | "adaptive" = aspectRatio;
  if (mode === "image-to-video") {
    sdkAspectRatio = "adaptive";
    warnings.push(
      `Image-to-video inherits the source image ratio. Framing for ${aspectRatio} was still appended — provide a ${aspectRatio} source image (and CTA card) for Performance Max.`,
    );
  }

  return {
    aspectRatio,
    framedPrompt,
    duration,
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

export class SeedanceClient {
  private readonly apiKey: string;
  private readonly model: string;
  private readonly baseURL: string;
  private readonly provider: SeedanceProvider;
  private readonly pollIntervalMs: number;
  private readonly pollTimeoutMs: number;

  constructor(config: SeedanceClientConfig = {}) {
    this.provider = resolveProvider(config);
    this.apiKey = resolveApiKey(config, this.provider);
    this.model =
      config.model ??
      process.env.SEEDANCE_MODEL ??
      (this.provider === "seevio" ? DEFAULT_SEEVIO_MODEL : "dreamina-seedance-2-0-260128");
    this.baseURL =
      config.baseURL ??
      (this.provider === "seevio" ? SEEVIO_BASE_URL : "https://ark.ap-southeast.bytepluses.com/api/v3");
    this.pollIntervalMs = config.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
    this.pollTimeoutMs = config.pollTimeoutMs ?? DEFAULT_POLL_TIMEOUT_MS;
  }

  getModel(): string {
    return this.model;
  }

  getProvider(): SeedanceProvider {
    return this.provider;
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
      provider: this.provider,
      model: this.model,
      aspectRatio: prepared.aspectRatio,
      duration: prepared.duration,
      mode: prepared.mode,
      resolution: prepared.resolution,
      framingApplied: hasFramingRule(prepared.framedPrompt, prepared.aspectRatio),
    });

    for (const warning of prepared.warnings) {
      logger.warn(warning);
    }

    try {
      const result =
        this.provider === "seevio"
          ? await this.generateViaSeevio(options, prepared, started)
          : await this.generateViaByteDance(options, prepared, started);

      logger.info("Seedance generation complete", {
        aspectRatio: result.aspectRatio,
        elapsedMs: result.elapsedMs,
        videoPath: result.videoPath,
        taskId: result.taskId,
      });

      return result;
    } catch (error) {
      const elapsedMs = Date.now() - started;
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

  private async generateViaSeevio(
    options: ParsedGenerateAdOptions,
    prepared: PreparedGeneration,
    started: number,
  ): Promise<GenerateAdResult> {
    const api = new SeevioApi(this.apiKey, this.baseURL);
    const payload = buildSeevioPayload(options, prepared, this.model);
    const created = await api.createTask(payload);
    const task = await api.waitForVideo(created.taskId ?? "", {
      intervalMs: this.pollIntervalMs,
      timeoutMs: this.pollTimeoutMs,
    });

    const videoUrl = task.data?.results?.[0];
    if (!videoUrl) {
      throw new Error(`Seevio task ${created.taskId} completed with no video URL.`);
    }

    let videoPath: string | undefined;
    if (!options.skipDownload) {
      videoPath = await this.persistVideo(
        { url: videoUrl },
        options.outputDir ?? DEFAULT_OUTPUT_DIR,
        defaultFileName(prepared.aspectRatio),
      );
    }

    return {
      aspectRatio: prepared.aspectRatio,
      prompt: options.prompt,
      framedPrompt: prepared.framedPrompt,
      duration: prepared.duration,
      model: this.model,
      resolution: prepared.resolution,
      pixelResolution: prepared.pixelResolution,
      mode: prepared.mode,
      videoUrl,
      videoPath,
      taskId: created.taskId,
      warnings: prepared.warnings,
      elapsedMs: Date.now() - started,
    };
  }

  private async generateViaByteDance(
    options: ParsedGenerateAdOptions,
    prepared: PreparedGeneration,
    started: number,
  ): Promise<GenerateAdResult> {
    const byteDance = createByteDance({
      apiKey: this.apiKey,
      baseURL: this.baseURL,
    });

    const prompt = options.image
      ? { text: prepared.framedPrompt, image: options.image }
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
          bytedance: {
            watermark: options.watermark,
            ...(options.generateAudio != null ? { generateAudio: options.generateAudio } : {}),
            ...(options.lastFrameImage ? { lastFrameImage: options.lastFrameImage } : {}),
            ...(options.referenceImages?.length ? { referenceImages: options.referenceImages } : {}),
            ...(options.referenceVideos?.length ? { referenceVideos: options.referenceVideos } : {}),
            ...(options.referenceAudio?.length ? { referenceAudio: options.referenceAudio } : {}),
            ...(options.cameraFixed != null ? { cameraFixed: options.cameraFixed } : {}),
          },
        },
      });

      const taskId =
        typeof providerMetadata === "object" &&
        providerMetadata &&
        "bytedance" in providerMetadata &&
        typeof (providerMetadata as { bytedance?: { taskId?: string } }).bytedance?.taskId ===
          "string"
          ? (providerMetadata as { bytedance: { taskId: string } }).bytedance.taskId
          : undefined;

      let videoPath: string | undefined;
      if (!options.skipDownload) {
        videoPath = await this.persistVideo(
          video,
          options.outputDir ?? DEFAULT_OUTPUT_DIR,
          defaultFileName(prepared.aspectRatio),
        );
      }

      return {
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
        warnings: [
          ...prepared.warnings,
          ...(sdkWarnings ?? []).map((warning) =>
            typeof warning === "string" ? warning : JSON.stringify(warning),
          ),
        ],
        elapsedMs: Date.now() - started,
      };
    } catch (error) {
      if (NoVideoGeneratedError.isInstance(error)) {
        throw new Error(
          `BytePlus generated no video: ${String(error.cause ?? error.message)}`,
          { cause: error },
        );
      }
      throw error;
    }
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
      logger.info("Downloaded generated video", {
        outputPath,
        bytes: bytes.byteLength,
      });
      return outputPath;
    }

    throw new Error("Seedance returned a video object with no bytes, base64, or URL.");
  }
}

export const clientDefaults = {
  model: DEFAULT_SEEVIO_MODEL,
  duration: DEFAULT_DURATION_SECONDS,
  resolution: DEFAULT_RESOLUTION,
  outputDir: DEFAULT_OUTPUT_DIR,
};
