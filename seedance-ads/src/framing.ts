import type { AspectRatio } from "./types.ts";

/**
 * Framing instructions that MUST be appended to every Seedance prompt.
 *
 * These are Google Ads composition rules, not optional style hints:
 * each ratio has a distinct shot language and a 3-second full-frame CTA hold.
 * Keep the wording stable so QA agents can assert exact inclusion.
 */
export const FRAMING_RULES: Record<AspectRatio, string> = {
  "9:16":
    "Frame vertically for 9:16 mobile. Keep the subject and any action centered in the middle third. Prefer tighter shots. Leave room above and below for the end card. End on the uploaded CTA card filling the full 9:16 frame for the final 3 seconds.",
  "1:1":
    "Frame for a 1:1 square. Center the composition. Use medium shots with balanced headroom. End on the uploaded CTA card filling the full 1:1 frame for the final 3 seconds.",
  "16:9":
    "Frame cinematically for 16:9 widescreen. Prefer wider establishing shots. Place the subject slightly off-center with clean negative space. End on the uploaded CTA card filling the full 16:9 frame for the final 3 seconds.",
};

const FRAMING_SEPARATOR = "\n\n";

/**
 * Build the prompt that is actually sent to Seedance.
 * Always appends the aspect-ratio framing rule. Callers must not
 * concatenate framing themselves — that would duplicate the instruction.
 */
export function buildPrompt(userPrompt: string, aspectRatio: AspectRatio): string {
  const trimmed = userPrompt.trim();
  const framing = FRAMING_RULES[aspectRatio];

  if (!trimmed) {
    throw new Error("Cannot build a Seedance prompt from an empty string.");
  }

  if (trimmed.includes(framing)) {
    return trimmed;
  }

  return `${trimmed}${FRAMING_SEPARATOR}${framing}`;
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
