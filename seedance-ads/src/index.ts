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
  VIDEO_RESOLUTIONS,
  aspectRatioSchema,
  generateAdOptionsSchema,
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
  VideoResolution,
} from "./types.ts";

export {
  FRAMING_RULES,
  buildPrompt,
  getFramingRule,
  hasFramingRule,
  listFramingRules,
} from "./framing.ts";

export { SeedanceClient, prepareGeneration } from "./client.ts";
export { generateFullAdSet, generateSingleAd, getDefaultClient } from "./generate.ts";

export type {
  AssetManager,
  PromptEngineer,
  QaAgent,
  QaVerdict,
  StoredAsset,
  VariantFactory,
} from "./agents/contracts.ts";
