import type { AspectRatio, GenerateAdOptions } from "../types.ts";
import { REFRAME_BODY_SECONDS } from "../types.ts";

export const OLS_SERVICES = [
  "estate-sales",
  "liquidation",
  "downsizing",
  "cleanouts",
  "listing-prep",
  "appraisals",
  "jewelry",
] as const;

export type OlsService = (typeof OLS_SERVICES)[number];

const NO_MONEY_UPFRONT = "No money upfront - we do the work, you get paid.";

/** SuperScale voiceover lines. Only estate-sales may use the no-money-upfront claim. */
export const SERVICE_VOICEOVER: Record<OlsService, string> = {
  "estate-sales":
    "A house full of memories can feel overwhelming. We handle the whole estate sale for you, from setup to sold. No money upfront - we do the work, you get paid.",
  liquidation:
    "When an entire property needs to be cleared, you shouldn't have to do it alone. Whole-home liquidation, handled start to finish, so you can move forward.",
  downsizing:
    "Moving to a smaller home is a big step. We help you sort, pack, and sell what you don't need, so you can downsize without the stress.",
  cleanouts:
    "Some homes need more than a cleanup, and that's okay. We clear it with care and zero judgment, room by room, until it feels like home again.",
  "listing-prep":
    "Before your property hits the market, it has to be cleared and ready. We take it from full house to market-ready, so it shows its best.",
  appraisals:
    "Not sure what your belongings are actually worth? Our certified appraiser examines each piece and gives you a clear, professional valuation, so you know what it's really worth.",
  jewelry:
    "That old estate jewelry sitting in a drawer could be worth more than you think. We evaluate every piece, gold and stones, and turn estate jewelry into cash.",
};

export const SERVICE_LABEL: Record<OlsService, string> = {
  "estate-sales": "estate sales",
  liquidation: "whole-home liquidation",
  downsizing: "downsizing and moving",
  cleanouts: "estate and hoarding cleanouts",
  "listing-prep": "real estate listing prep",
  appraisals: "personal property appraisals",
  jewelry: "estate jewelry buying",
};

const RECREATE_CORE = `Recreate [Video 1] as a new Google Ads clip in this aspect ratio. Keep the same documentary story, cuts, pacing, Tampa Bay residential feel, and warm female voiceover. Do not invent people, rooms, or objects that are not in [Video 1]. No on-screen text, logos, captions, or watermarks. [Image 1] is the branded CTA card — reserve the last 3 seconds so the story resolves into that card filling the full frame.`;

export function buildReframePrompt(service: OlsService, _aspectRatio: AspectRatio): string {
  const voiceover = SERVICE_VOICEOVER[service];
  const label = SERVICE_LABEL[service];
  return [
    RECREATE_CORE,
    `This is an Organizing Life Services ${label} ad.`,
    `Voiceover (keep verbatim): "${voiceover}"`,
  ].join("\n\n");
}

export function assertNoMoneyUpfrontGuard(service: OlsService, prompt: string): void {
  if (service === "estate-sales") return;
  if (prompt.toLowerCase().includes("no money upfront")) {
    throw new Error(
      `${service} prompt must not include the estate-sales "${NO_MONEY_UPFRONT}" claim.`,
    );
  }
}

export function buildReframeGenerateOptions(opts: {
  service: OlsService;
  aspectRatio: AspectRatio;
  sourceVideoUrl: string;
  ctaImageUrl: string;
  outputDir?: string;
}): GenerateAdOptions {
  const prompt = buildReframePrompt(opts.service, opts.aspectRatio);
  assertNoMoneyUpfrontGuard(opts.service, prompt);
  return {
    prompt,
    aspectRatio: opts.aspectRatio,
    duration: REFRAME_BODY_SECONDS,
    lastFrameImage: opts.ctaImageUrl,
    referenceVideos: [opts.sourceVideoUrl],
    generateAudio: true,
    outputDir: opts.outputDir,
  };
}
