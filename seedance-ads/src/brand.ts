import type { GenerateAdOptions } from "./types.ts";

/**
 * First-party Organizing Life Services facts for Google Ads creatives.
 * Keep this aligned with the public site and docs/seo.md — do not invent
 * people, houses, uniforms, or services that are not listed here.
 */
export const OLS_BRAND = {
  legalName: "Organizing Life Services",
  shortName: "OLS",
  phone: "(727) 542-6028",
  email: "info@organizinglifeservices.com",
  website: "https://organizinglifeservices.com",
  foundedYear: 2010,
  tagline: "Licensed, Trusted & Insured Since 2010",
  services: [
    "professionally managed estate sales",
    "personal-property appraisals",
    "senior downsizing",
    "house cleanouts",
  ],
  counties: ["Pinellas", "Pasco", "Hillsborough", "Hernando", "Citrus"],
  region: "Tampa Bay, Florida",
} as const;

export type BrandReference = {
  url: string;
  label: string;
  /** What the photo actually shows. Used in the prompt as [Image N]. */
  description: string;
};

/**
 * Public Shopify CDN stills from real OLS sales — not homepage stock art.
 * The Palm Harbor / Pinellas marketing JPEGs on the site are stock family
 * photos and must not be used as visual source.
 */
export const OLS_REFERENCE_IMAGES: readonly BrandReference[] = [
  {
    url: "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/OrganizingLifeServices_Logo_final.jpg?v=1775281954",
    label: "OLS logo",
    description:
      "OLS maroon-and-charcoal house-mark logo with the tagline Licensed, Trusted & Insured Since 2010. Brand lockup only — do not restyle it or invent other logos.",
  },
  {
    url: "https://cdn.shopify.com/s/files/1/0294/7966/5708/t/7/assets/photo-mar1622516pm-Akl.jpg",
    label: "East Lake Woodlands teak credenza",
    description:
      "Real East Lake Woodlands sale: mid-century teak credenza and glass-door hutch with pottery, glassware, and shells on a light carpet.",
  },
  {
    url: "https://cdn.shopify.com/s/files/1/0294/7966/5708/t/7/assets/photo-mar1624050pm-bUr.jpg",
    label: "New Port Richey kitchen cabinet",
    description:
      "Real New Port Richey sale: white kitchen cabinet shelves staged with pitchers, stacked bowls, floral plates, and glassware.",
  },
  {
    url: "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/Photo_Dec_11_2024_1_18_07_PM.jpg",
    label: "Largo vintage Pyrex",
    description:
      "Real Largo sale: vintage green-and-white floral Pyrex casserole bowls with glass lids on a wood cabinet shelf.",
  },
  {
    url: "https://cdn.shopify.com/s/files/1/0294/7966/5708/t/7/assets/photo-mar1622758pm-ArU.jpg",
    label: "New Port Richey living room",
    description:
      "Real New Port Richey sale: round glass coffee table on a black cylinder base, black leather seating with colorful pillows, tan carpet.",
  },
  {
    url: "https://cdn.shopify.com/s/files/1/0294/7966/5708/files/stacked-bracelets.jpg?v=1614294929",
    label: "Estate jewelry",
    description:
      "Real OLS estate jewelry: gold bangles, a crystal channel bracelet, and an arrow cuff on a white surface.",
  },
];

export const TEXT_TO_VIDEO_ACCURACY_WARNING =
  "Text-to-video invents people, homes, and branding. For OLS ads, use --brief ols (real sale photos) or pass --reference-image URLs from first-party galleries.";

const REFERENCE_GUIDANCE =
  "Use the numbered reference stills as the only visual source. Keep furniture, rooms, and objects faithful to those photos. Do not invent people, uniforms, houses, logos, phone numbers, websites, watermarks, or text overlays that are not in the references.";

export function appendReferenceGuidance(prompt: string, referenceCount: number): string {
  if (referenceCount <= 0) return prompt;
  if (/\[Image\s*1\]/i.test(prompt)) return prompt;

  const labels = Array.from({ length: referenceCount }, (_, index) => `[Image ${index + 1}]`).join(
    ", ",
  );
  return `${prompt.trim()}\n\n${REFERENCE_GUIDANCE} References: ${labels}.`;
}

export function buildOlsPrompt(): string {
  const imageLines = OLS_REFERENCE_IMAGES.map(
    (image, index) => `[Image ${index + 1}] ${image.description}`,
  ).join("\n");

  return [
    `Photorealistic documentary Google Ads clip for ${OLS_BRAND.legalName} (${OLS_BRAND.shortName}), a licensed estate-sale company in ${OLS_BRAND.region} since ${OLS_BRAND.foundedYear}.`,
    `Services shown only as staged household contents from real sales: ${OLS_BRAND.services.join(", ")}. Coverage: ${OLS_BRAND.counties.join(", ")} counties. Do not invent people, staff uniforms, talking heads, fake houses, or on-screen text.`,
    "",
    "Visual source — real first-party sale photos:",
    imageLines,
    "",
    "Shot list, natural Florida-home daylight, handheld-stable, no voiceover, no text overlays:",
    "0-2s: Slow push across [Image 2] teak credenza. Keep the wood, glass doors, pottery, and shells true to the photo.",
    "2-4s: Gentle pan along [Image 3] kitchen shelves, then a beat on [Image 4] Pyrex bowls.",
    "4-6s: Close, shallow-focus move across [Image 6] jewelry.",
    "6-8s: Pull back to [Image 5] living-room table and hold. [Image 1] is brand identity only — do not animate a fake end card from it unless a last-frame CTA image was uploaded.",
  ].join("\n");
}

export type NamedBrief = "ols";

export function resolveNamedBrief(id: NamedBrief): Pick<GenerateAdOptions, "prompt" | "referenceImages"> {
  if (id !== "ols") {
    throw new Error(`Unknown brief "${id}". Supported: ols`);
  }
  return {
    prompt: buildOlsPrompt(),
    referenceImages: OLS_REFERENCE_IMAGES.map((image) => image.url),
  };
}
