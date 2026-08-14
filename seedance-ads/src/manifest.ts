import { z } from "zod";
import { OLS_SERVICES } from "./prompts/reframe.ts";

const httpUrl = z
  .string()
  .min(1)
  .refine((value) => /^https?:\/\//i.test(value), {
    message: "Must be a public HTTP(S) URL. Local files are not uploaded to Seevio.",
  });

export const reframeVideoSchema = z.object({
  id: z
    .string()
    .min(1)
    .regex(/^[a-z0-9-]+$/, "id must be lowercase kebab-case"),
  service: z.enum(OLS_SERVICES),
  sourceVideoUrl: httpUrl,
});

export const reframeManifestSchema = z.object({
  ctaImageUrl: httpUrl,
  outputDir: z.string().min(1).default("output"),
  videos: z.array(reframeVideoSchema).min(1),
});

export type ReframeVideo = z.infer<typeof reframeVideoSchema>;
export type ReframeManifest = z.output<typeof reframeManifestSchema>;
export type ReframeManifestInput = z.input<typeof reframeManifestSchema>;

export function parseReframeManifest(raw: unknown): ReframeManifest {
  return reframeManifestSchema.parse(raw);
}

export function filterManifestByService(
  manifest: ReframeManifest,
  service: ReframeVideo["service"],
): ReframeManifest {
  const videos = manifest.videos.filter((video) => video.service === service);
  if (videos.length === 0) {
    throw new Error(`No videos in the manifest for service "${service}".`);
  }
  return { ...manifest, videos };
}
