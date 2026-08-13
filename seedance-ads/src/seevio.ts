import { logger } from "./logger.ts";
import {
  DEFAULT_SEEDANCE_MODEL,
  type AspectRatio,
  type ParsedGenerateAdOptions,
  type PreparedGeneration,
} from "./types.ts";

export const SEEVIO_BASE_URL = "https://api.seevio.ai";
export const DEFAULT_SEEVIO_MODEL = DEFAULT_SEEDANCE_MODEL;

export type SeevioGenerationType =
  | "text-to-video"
  | "image-to-video"
  | "reference-to-video";

export type SeevioCreateTaskResponse = {
  taskId?: string;
  credits?: number;
  error?: { code?: string; message?: string };
};

export type SeevioTaskStatus = "queued" | "generating" | "completed" | "failed" | string;

export type SeevioTaskResponse = {
  id?: string;
  status?: SeevioTaskStatus;
  credits?: number;
  failed_reason?: string | null;
  data?: {
    results?: string[];
    video_expires_at?: string;
    last_frame_url?: string | null;
    processing_time?: number;
    failed_reason?: string;
  };
  error?: { code?: string; message?: string };
};

export type SeevioPayload = {
  model: string;
  input: {
    prompt: string;
    generation_type: SeevioGenerationType;
    duration: number;
    aspect_ratio: AspectRatio | "adaptive";
    resolution: string;
    generate_audio: boolean;
    watermark: boolean;
    image_urls?: string[];
    video_urls?: string[];
    audio_urls?: string[];
    seed?: number;
  };
};

function isPublicHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function requirePublicUrl(value: string, label: string): string {
  if (!isPublicHttpUrl(value)) {
    throw new Error(
      `${label} must be a public HTTP(S) URL for the Seevio API. Local files are not uploaded.`,
    );
  }
  return value;
}

function apiErrorMessage(status: number, body: unknown): string {
  if (body && typeof body === "object" && "error" in body) {
    const error = (body as { error?: { code?: string; message?: string } }).error;
    const code = error?.code ? `${error.code}: ` : "";
    const message = error?.message ?? JSON.stringify(body);
    return `Seevio HTTP ${status} ${code}${message}`;
  }
  return `Seevio HTTP ${status}: ${typeof body === "string" ? body : JSON.stringify(body)}`;
}

/**
 * Build the Seevio request body. Framing is already on prepared.framedPrompt.
 */
export function buildSeevioPayload(
  options: ParsedGenerateAdOptions,
  prepared: PreparedGeneration,
  model: string,
): SeevioPayload {
  const hasReferences = Boolean(
    options.referenceImages?.length ||
      options.referenceVideos?.length ||
      options.referenceAudio?.length,
  );

  let generationType: SeevioGenerationType = "text-to-video";
  if (hasReferences) {
    generationType = "reference-to-video";
  } else if (options.image) {
    generationType = "image-to-video";
  }

  const imageUrls: string[] = [];
  if (options.image) {
    imageUrls.push(requirePublicUrl(options.image, "image"));
  }
  if (options.lastFrameImage && generationType === "image-to-video") {
    imageUrls.push(requirePublicUrl(options.lastFrameImage, "lastFrameImage"));
  }
  if (options.referenceImages?.length) {
    for (const [index, url] of options.referenceImages.entries()) {
      imageUrls.push(requirePublicUrl(url, `referenceImages[${index}]`));
    }
  }
  // reference-to-video cannot use first+last-frame mode. Put the CTA first
  // so prompts can call it [Image 1].
  if (generationType === "reference-to-video" && options.lastFrameImage) {
    const cta = requirePublicUrl(options.lastFrameImage, "lastFrameImage");
    if (!imageUrls.includes(cta)) {
      imageUrls.unshift(cta);
    }
  }

  const payload: SeevioPayload = {
    model,
    input: {
      prompt: prepared.framedPrompt,
      generation_type: generationType,
      duration: prepared.duration,
      aspect_ratio: prepared.sdkAspectRatio,
      resolution: prepared.resolution,
      generate_audio: options.generateAudio ?? true,
      watermark: options.watermark,
    },
  };

  if (imageUrls.length > 0) {
    payload.input.image_urls = imageUrls;
  }
  if (options.referenceVideos?.length) {
    payload.input.video_urls = options.referenceVideos.map((url, index) =>
      requirePublicUrl(url, `referenceVideos[${index}]`),
    );
  }
  if (options.referenceAudio?.length) {
    payload.input.audio_urls = options.referenceAudio.map((url, index) =>
      requirePublicUrl(url, `referenceAudio[${index}]`),
    );
  }
  if (options.seed != null && !model.includes("2-5")) {
    payload.input.seed = options.seed;
  }

  return payload;
}

export class SeevioApi {
  constructor(
    private readonly apiKey: string,
    private readonly baseURL: string = SEEVIO_BASE_URL,
  ) {}

  async createTask(payload: SeevioPayload): Promise<SeevioCreateTaskResponse> {
    const response = await fetch(`${this.baseURL}/v1/videos/generations`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    const body = (await response.json().catch(() => ({}))) as SeevioCreateTaskResponse;
    if (!response.ok) {
      throw new Error(apiErrorMessage(response.status, body));
    }
    if (!body.taskId) {
      throw new Error(`Seevio accepted the request but returned no taskId: ${JSON.stringify(body)}`);
    }
    logger.info("Seevio task accepted", { taskId: body.taskId, credits: body.credits });
    return body;
  }

  async getTask(taskId: string): Promise<SeevioTaskResponse> {
    const response = await fetch(`${this.baseURL}/v1/tasks/${encodeURIComponent(taskId)}`, {
      headers: {
        Authorization: `Bearer ${this.apiKey}`,
      },
    });
    const body = (await response.json().catch(() => ({}))) as SeevioTaskResponse;
    if (!response.ok) {
      throw new Error(apiErrorMessage(response.status, body));
    }
    return body;
  }

  async waitForVideo(
    taskId: string,
    opts: { intervalMs: number; timeoutMs: number },
  ): Promise<SeevioTaskResponse> {
    const started = Date.now();
    const intervalMs = Math.max(opts.intervalMs, 10_000);

    while (Date.now() - started < opts.timeoutMs) {
      const task = await this.getTask(taskId);
      logger.info("Seevio task status", {
        taskId,
        status: task.status,
        elapsedMs: Date.now() - started,
      });

      if (task.status === "completed") {
        return task;
      }
      if (task.status === "failed") {
        const reason = task.failed_reason ?? task.data?.failed_reason ?? "unknown failure";
        throw new Error(`Seevio task ${taskId} failed: ${reason}`);
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }

    throw new Error(
      `Seevio task ${taskId} timed out after ${opts.timeoutMs}ms (still generating).`,
    );
  }
}
