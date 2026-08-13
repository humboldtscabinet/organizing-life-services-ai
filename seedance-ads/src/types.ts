import { z } from "zod";

/**
 * Google Ads / Performance Max requires this exact trio.
 * Additional Seedance ratios exist (4:3, 3:4, 21:9) but are out of scope
 * until a future Variant Factory agent needs them.
 */
export const ASPECT_RATIOS = ["9:16", "1:1", "16:9"] as const;
export type AspectRatio = (typeof ASPECT_RATIOS)[number];

export const aspectRatioSchema = z.enum(ASPECT_RATIOS);

export const VIDEO_RESOLUTIONS = ["480p", "720p", "1080p"] as const;
export type VideoResolution = (typeof VIDEO_RESOLUTIONS)[number];

export const videoResolutionSchema = z.enum(VIDEO_RESOLUTIONS);

/**
 * Pixel sizes the ByteDance provider maps back to 480p / 720p / 1080p.
 * Seedance 2.0 currently supports 480p and 720p only; 1080p is clamped.
 */
export const PIXEL_RESOLUTION: Record<
  VideoResolution,
  Record<AspectRatio, `${number}x${number}`>
> = {
  "480p": {
    "9:16": "480x864",
    "1:1": "640x640",
    "16:9": "864x480",
  },
  "720p": {
    "9:16": "720x1280",
    "1:1": "960x960",
    "16:9": "1280x720",
  },
  "1080p": {
    "9:16": "1080x1920",
    "1:1": "1440x1440",
    "16:9": "1920x1080",
  },
};

export function parsePixelSize(size: `${number}x${number}`): { width: number; height: number } {
  const [width, height] = size.split("x").map((part) => Number(part));
  if (!width || !height) {
    throw new Error(`Invalid pixel size: ${size}`);
  }
  return { width, height };
}

export function canvasSize(
  aspectRatio: AspectRatio,
  resolution: VideoResolution = "720p",
): { width: number; height: number } {
  return parsePixelSize(PIXEL_RESOLUTION[resolution][aspectRatio]);
}

export const DEFAULT_SEEDANCE_MODEL = "seedance-2-5";
export const DEFAULT_DURATION_SECONDS = 8;
export const DEFAULT_RESOLUTION: VideoResolution = "720p";
export const CTA_HOLD_SECONDS = 3;
/** Seedance body length for a reframe job. ffmpeg then appends CTA_HOLD_SECONDS. */
export const REFRAME_BODY_SECONDS = 16;
export const REFRAME_TOTAL_SECONDS = REFRAME_BODY_SECONDS + CTA_HOLD_SECONDS;

export type SeedanceProvider = "seevio" | "bytedance";

export const generateAdOptionsSchema = z.object({
  /** Creative brief / scene description. Framing is appended automatically. */
  prompt: z.string().min(1, "prompt is required"),
  aspectRatio: aspectRatioSchema.default("9:16"),
  /** Clip length in seconds. Seedance 2.5 supports 4–30s; 2.0 supports 4–15s. */
  duration: z.number().int().min(4).max(30).default(DEFAULT_DURATION_SECONDS),
  /**
   * First-frame image for image-to-video.
   * HTTP(S) URL, data URI, or local filesystem path.
   */
  image: z.string().min(1).optional(),
  /** Last-frame / CTA card image (URL or local path). */
  lastFrameImage: z.string().min(1).optional(),
  /** Multi-reference stills (URLs). Mention them as [Image 1], [Image 2], … */
  referenceImages: z.array(z.string().min(1)).max(12).optional(),
  /** Seedance 2.5 reference clips (up to 10; combined duration ≤ 30s). */
  referenceVideos: z.array(z.string().min(1)).max(10).optional(),
  /** Seedance 2.5 reference audio (up to 10; combined duration ≤ 30s). */
  referenceAudio: z.array(z.string().min(1)).max(10).optional(),
  generateAudio: z.boolean().optional(),
  watermark: z.boolean().default(false),
  cameraFixed: z.boolean().optional(),
  resolution: videoResolutionSchema.default(DEFAULT_RESOLUTION),
  seed: z.number().int().optional(),
  /** Directory for downloaded MP4s. Defaults to ./output */
  outputDir: z.string().min(1).optional(),
  /** Skip writing a file and only return the remote URL. */
  skipDownload: z.boolean().optional(),
});

export type GenerateAdOptions = z.input<typeof generateAdOptionsSchema>;
export type ParsedGenerateAdOptions = z.output<typeof generateAdOptionsSchema>;

export interface GenerateAdResult {
  aspectRatio: AspectRatio;
  /** User prompt before framing was appended. */
  prompt: string;
  /** Full prompt actually sent to Seedance, including the framing rule. */
  framedPrompt: string;
  duration: number;
  model: string;
  resolution: VideoResolution;
  pixelResolution: `${number}x${number}`;
  mode: "text-to-video" | "image-to-video" | "reference-to-video";
  /** Remote MP4 URL when the SDK exposes one (ModelArk URLs expire). */
  videoUrl?: string;
  /** Local path if the file was downloaded. */
  videoPath?: string;
  /** ModelArk task id, when the provider returns it. */
  taskId?: string;
  warnings: string[];
  elapsedMs: number;
}

export interface GenerateAllRatiosResult {
  results: GenerateAdResult[];
  failures: Array<{ aspectRatio: AspectRatio; error: string }>;
}

export interface SeedanceClientConfig {
  apiKey?: string;
  model?: string;
  baseURL?: string;
  /** seevio = Seevio/seedance2.ai (default). bytedance = BytePlus ModelArk. */
  provider?: SeedanceProvider;
  /** Poll interval while waiting (Seevio requires >= 10s). */
  pollIntervalMs?: number;
  /** Give up after this many ms (default 15 minutes). */
  pollTimeoutMs?: number;
}

/**
 * Internal request built by the single generation pipeline.
 * Tests and future agents (Prompt Engineer, QA) can inspect this
 * to confirm framing was applied before any API call.
 */
export interface PreparedGeneration {
  aspectRatio: AspectRatio;
  framedPrompt: string;
  duration: number;
  resolution: VideoResolution;
  pixelResolution: `${number}x${number}`;
  mode: "text-to-video" | "image-to-video" | "reference-to-video";
  warnings: string[];
  sdkAspectRatio: AspectRatio | "adaptive";
}
