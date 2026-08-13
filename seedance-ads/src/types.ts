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

export const DEFAULT_SEEDANCE_MODEL = "dreamina-seedance-2-0-260128";
export const DEFAULT_DURATION_SECONDS = 8;
export const DEFAULT_RESOLUTION: VideoResolution = "720p";
export const CTA_HOLD_SECONDS = 3;

export const generateAdOptionsSchema = z.object({
  /** Creative brief / scene description. Framing is appended automatically. */
  prompt: z.string().min(1, "prompt is required"),
  aspectRatio: aspectRatioSchema.default("9:16"),
  /** Clip length in seconds. Seedance 2.0 supports 4–15s. */
  duration: z.number().int().min(4).max(15).default(DEFAULT_DURATION_SECONDS),
  /**
   * First-frame image for image-to-video.
   * HTTP(S) URL, data URI, or local filesystem path.
   */
  image: z.string().min(1).optional(),
  /** Last-frame / CTA card image (URL or local path). */
  lastFrameImage: z.string().min(1).optional(),
  /** Multi-reference stills (URLs). Mention them as [Image 1], [Image 2], … */
  referenceImages: z.array(z.string().min(1)).max(4).optional(),
  /** Seedance 2.0 reference clips (up to 3, max 15s each). */
  referenceVideos: z.array(z.string().min(1)).max(3).optional(),
  /** Seedance 2.0 reference audio (up to 3, max 15s each). */
  referenceAudio: z.array(z.string().min(1)).max(3).optional(),
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
  mode: "text-to-video" | "image-to-video";
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
  /** Poll interval while waiting for ModelArk (default 5s). */
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
  mode: "text-to-video" | "image-to-video";
  warnings: string[];
  sdkAspectRatio: AspectRatio | "adaptive";
}
