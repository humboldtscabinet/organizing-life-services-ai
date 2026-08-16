/**
 * Exact CTA copy from the Shopify 9:16 master
 * (OLS_CTA_Card_Google_Ads.png). Do not paraphrase, wrap differently
 * in a way that changes wording, or send these strings through Seedance.
 * The logo lockup (ORGANIZING / LIFE SERVICES / tagline) is cropped from
 * the master PNG so those letterforms are never re-typeset.
 */
export const CTA_COPY = {
  headline: "Ready to Get Started?",
  servicesLine1: "Estate Sales - Liquidation - Downsizing",
  servicesLine2: "Cleanouts - Appraisals - Jewelry Buying",
  button: "Get Your Free Consultation",
  url: "organizinglifeservices.com",
  footer: "PROFESSIONAL - RELIABLE - TRUSTED",
} as const;

export type CtaCopy = typeof CTA_COPY;

export const CTA_COPY_STRINGS: readonly string[] = [
  CTA_COPY.headline,
  CTA_COPY.servicesLine1,
  CTA_COPY.servicesLine2,
  CTA_COPY.button,
  CTA_COPY.url,
  CTA_COPY.footer,
];

/** Cream used behind padded canvases and native layouts. */
export const CTA_BACKGROUND = "#F7F4EE";
export const CTA_PAD_COLOR = "0xF7F4EE";
export const CTA_INK = "#3A3A3A";
export const CTA_GOLD = "#C4A04A";
export const CTA_BUTTON_TEXT = "#FFFFFF";

/**
 * Lockup crop on the 1536×2752 Shopify master: square mark, ORGANIZING,
 * LIFE SERVICES, and "Licensed, Trusted & Insured Since 2010".
 */
export const CTA_MASTER_SIZE = { width: 1536, height: 2752 } as const;
export const CTA_LOCKUP_CROP = { x: 300, y: 80, width: 936, height: 1100 } as const;
