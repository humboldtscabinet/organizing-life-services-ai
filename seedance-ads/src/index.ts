/**
 * Public API for seedance-ads.
 *
 * Generation always goes through SeedanceClient / generateSingleAd /
 * generateFullAdSet so the Google Ads framing rules cannot be skipped.
 */

export {
  ASPECT_RATIOS,
  CTA_HOLD_SECONDS,
  DEFAULT_DURATION_SECONDS,
  DEFAULT_RESOLUTION,
  DEFAULT_SEEDANCE_MODEL,
  PIXEL_RESOLUTION,
  REFRAME_BODY_SECONDS,
  REFRAME_TOTAL_SECONDS,
  VIDEO_RESOLUTIONS,
  aspectRatioSchema,
  canvasSize,
  generateAdOptionsSchema,
  parsePixelSize,
  seedanceDurationSeconds,
  videoResolutionSchema,
} from "./types.ts";
export type {
  AspectRatio,
  GenerateAdOptions,
  GenerateAdResult,
  GenerateAllRatiosResult,
  ParsedGenerateAdOptions,
  PreparedGeneration,
  SeedanceClientConfig,
  SeedanceProvider,
  VideoResolution,
} from "./types.ts";

export {
  FRAMING_CTA_RULES,
  FRAMING_RULES,
  buildPrompt,
  getFramingRule,
  hasFramingRule,
  listFramingRules,
} from "./framing.ts";
export {
  OLS_BRAND,
  OLS_REFERENCE_IMAGES,
  TEXT_TO_VIDEO_ACCURACY_WARNING,
  appendReferenceGuidance,
  buildOlsPrompt,
  resolveNamedBrief,
} from "./brand.ts";
export type { BrandReference, NamedBrief } from "./brand.ts";

export { SeedanceClient, prepareGeneration } from "./client.ts";
export { buildSeevioPayload, SEEVIO_BASE_URL } from "./seevio.ts";
export { generateFullAdSet, generateSingleAd, getDefaultClient } from "./generate.ts";
export { parseReframeManifest, filterManifestByService, reframeManifestSchema } from "./manifest.ts";
export {
  OLS_SERVICES,
  SERVICE_VOICEOVER,
  buildReframePrompt,
  buildReframeGenerateOptions,
} from "./prompts/reframe.ts";
export type { OlsService } from "./prompts/reframe.ts";
export {
  writeAllCtaCanvases,
  writeCtaCanvas,
  cropCtaLockup,
  CTA_BACKGROUND,
  CTA_COPY,
  CTA_COPY_STRINGS,
  CTA_PAD_COLOR,
} from "./cta.ts";
export type { CtaLayout } from "./cta.ts";
export {
  appendCtaHold,
  downloadToFile,
  ffmpegAvailable,
  replaceEndingWithCta,
  requireFfmpeg,
} from "./compose.ts";

export type {
  AssetManager,
  PromptEngineer,
  QaAgent,
  QaVerdict,
  StoredAsset,
  VariantFactory,
} from "./agents/contracts.ts";
