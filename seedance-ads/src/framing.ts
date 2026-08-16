import type { AspectRatio } from "./types.ts";

/**
 * Framing instructions that MUST be appended to every Seedance prompt.
 *
 * These are Google Ads composition rules, not optional style hints.
 * A 3-second CTA hold is appended only when a last-frame image is provided.
 * Keep the wording stable so QA agents can assert exact inclusion.
 */
export const FRAMING_RULES: Record<AspectRatio, string> = {
  "9:16":
    "Frame vertically for 9:16 mobile. Keep the subject and any action centered in the middle third. Prefer tighter shots. Leave clean space at the top and bottom. Do not invent a logo, phone number, website, watermark, or end card.",
  "1:1":
    "Frame for a 1:1 square. Center the composition. Use medium shots with balanced headroom. Do not invent a logo, phone number, website, watermark, or end card.",
  "16:9":
    "Frame cinematically for 16:9 widescreen. Prefer wider establishing shots. Place the subject slightly off-center with clean negative space. Do not invent a logo, phone number, website, watermark, or end card.",
};

/** Appended only when a last-frame / CTA image was actually provided. */
export const FRAMING_CTA_RULES: Record<AspectRatio, string> = {
  "9:16":
    "End on the uploaded CTA card filling the full 9:16 frame for the final 3 seconds.",
  "1:1":
    "End on the uploaded CTA card filling the full 1:1 frame for the final 3 seconds.",
  "16:9":
    "End on the uploaded CTA card filling the full 16:9 frame for the final 3 seconds.",
};

const FRAMING_SEPARATOR = "\n\n";

/**
 * Build the prompt that is actually sent to Seedance.
 * Always appends the aspect-ratio framing rule. Callers must not
 * concatenate framing themselves — that would duplicate the instruction.
 */
export function buildPrompt(
  userPrompt: string,
  aspectRatio: AspectRatio,
  extras: { hasCtaCard?: boolean } = {},
): string {
  const trimmed = userPrompt.trim();
  const framing = FRAMING_RULES[aspectRatio];

  if (!trimmed) {
    throw new Error("Cannot build a Seedance prompt from an empty string.");
  }

  let prompt = trimmed.includes(framing)
    ? trimmed
    : `${trimmed}${FRAMING_SEPARATOR}${framing}`;

  if (extras.hasCtaCard) {
    const cta = FRAMING_CTA_RULES[aspectRatio];
    if (!prompt.includes(cta)) {
      prompt = `${prompt}${FRAMING_SEPARATOR}${cta}`;
    }
  }

  return prompt;
}

/** True when the given text already contains the canonical framing rule. */
export function hasFramingRule(prompt: string, aspectRatio: AspectRatio): boolean {
  return prompt.includes(FRAMING_RULES[aspectRatio]);
}

export function getFramingRule(aspectRatio: AspectRatio): string {
  return FRAMING_RULES[aspectRatio];
}

export function listFramingRules(): Readonly<Record<AspectRatio, string>> {
  return FRAMING_RULES;
}
