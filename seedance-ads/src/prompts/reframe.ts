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

/**
 * Seedance treats "no on-screen text" as captions/watermarks and still
 * paints fake lettering onto boxes. Real English labels are allowed;
 * gibberish is not. Keep this wording stable so tests can assert exact
 * inclusion.
 */
export const NO_INVENTED_TEXT_RULE =
  "Do not add captions, logos, watermarks, phone numbers, websites, or call-to-action graphics. Environmental text is allowed only when it is real English, correctly spelled, in focus, and relevant to the room — Kitchen, Books, Fragile, or empty printed label lines. Never paint gibberish, misspellings, fake brands, letter-scribbles, or invented product names on boxes, bins, tape, stickers, spines, newspapers, screens, tags, or framed art. If you cannot render a real word cleanly, leave that surface blank. Do not typeset the Organizing Life Services lockup or CTA; that card is added later in ffmpeg.";

const BOX_HEAVY_SERVICES = new Set<OlsService>([
  "liquidation",
  "downsizing",
  "cleanouts",
  "listing-prep",
  "estate-sales",
]);

export const BOX_HEAVY_TEXT_RULE =
  "This service shows many boxes and bins. Printed labels may stay if they are real English words in focus (Kitchen, Books, Fragile). Blank boxes and empty label lines are always correct. Gibberish, misspellings, and fake lettering on any box, lid, tape strip, or sticker are not.";

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

const RECREATE_CORE = `Recreate [Video 1] as a new Google Ads clip in this aspect ratio. Keep the same documentary story, cuts, pacing, Tampa Bay residential feel, and warm female voiceover. Do not invent people, rooms, or objects that are not in [Video 1]. No captions, logos, watermarks, phone numbers, or CTA graphics.

${NO_INVENTED_TEXT_RULE}

Skip the original end-card entirely. Do not recreate any logo screen, phone number, website, "Call Today" card, or call-to-action graphic from [Video 1]. End on live-action only. The branded CTA is added later in ffmpeg — do not generate one.`;

export function buildReframePrompt(service: OlsService, _aspectRatio: AspectRatio): string {
  const voiceover = SERVICE_VOICEOVER[service];
  const label = SERVICE_LABEL[service];
  const parts = [
    RECREATE_CORE,
    `This is an Organizing Life Services ${label} ad.`,
    `Voiceover (keep verbatim): "${voiceover}"`,
  ];
  if (BOX_HEAVY_SERVICES.has(service)) {
    parts.push(BOX_HEAVY_TEXT_RULE);
  }
  return parts.join("\n\n");
}

export function assertNoInventedTextRule(prompt: string): void {
  if (!prompt.includes(NO_INVENTED_TEXT_RULE)) {
    throw new Error("Reframe prompt is missing the no-invented-text rule.");
  }
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
  duration?: number;
  outputDir?: string;
}): GenerateAdOptions {
  const prompt = buildReframePrompt(opts.service, opts.aspectRatio);
  assertNoMoneyUpfrontGuard(opts.service, prompt);
  assertNoInventedTextRule(prompt);
  return {
    prompt,
    aspectRatio: opts.aspectRatio,
    duration: opts.duration ?? REFRAME_BODY_SECONDS,
    // Do not send the CTA still to Seedance. Passing it as lastFrameImage
    // makes the model render a card in the body, then ffmpeg would add
    // another. The Shopify file is composited on after generation.
    referenceVideos: [opts.sourceVideoUrl],
    generateAudio: true,
    outputDir: opts.outputDir,
  };
}
