/**
 * Classify OCR tokens from remake body frames.
 *
 * Real English labels (Kitchen, Books, Fragile) are allowed. Gibberish,
 * near-miss spellings of packing words, and Seedance-drawn CTA copy fail.
 * This is a shipping gate, not a credit refund — the Seevio job already ran.
 */

export type TokenVerdict = "ok" | "gibberish" | "misspelling" | "cta" | "ignored";

export type ClassifiedToken = {
  token: string;
  verdict: TokenVerdict;
  reason?: string;
};

export type SceneTextReport = {
  pass: boolean;
  tokens: ClassifiedToken[];
  failures: ClassifiedToken[];
  notes: string[];
};

/** Common moving-box / estate-sale labels. Compared case-insensitively. */
export const PACKING_LABELS: readonly string[] = [
  "FRAGILE",
  "HANDLE",
  "CARE",
  "THIS",
  "SIDE",
  "KEEP",
  "DRY",
  "HEAVY",
  "OPEN",
  "HERE",
  "KITCHEN",
  "PANTRY",
  "DISHES",
  "GLASS",
  "GLASSES",
  "CHINA",
  "CRYSTAL",
  "SILVER",
  "SILVERWARE",
  "FLATWARE",
  "STEMWARE",
  "BOOK",
  "BOOKS",
  "MEDIA",
  "CLOTHES",
  "CLOTHING",
  "LINEN",
  "LINENS",
  "TOWELS",
  "SHEETS",
  "PILLOWS",
  "BLANKETS",
  "BEDDING",
  "BATHROOM",
  "BEDROOM",
  "MASTER",
  "GUEST",
  "LIVING",
  "DINING",
  "OFFICE",
  "GARAGE",
  "ATTIC",
  "BASEMENT",
  "LAUNDRY",
  "STORAGE",
  "CLOSET",
  "HALL",
  "HALLWAY",
  "NURSERY",
  "KIDS",
  "TOYS",
  "TOOLS",
  "HARDWARE",
  "PAINT",
  "HOLIDAY",
  "CHRISTMAS",
  "WINTER",
  "SUMMER",
  "SPRING",
  "FALL",
  "MISC",
  "MISCELLANEOUS",
  "DONATE",
  "DONATION",
  "SELL",
  "SALE",
  "SOLD",
  "MOVING",
  "PACKING",
  "CONTENTS",
  "ROOM",
  "HOUSE",
  "HOME",
  "ESTATE",
  "JEWELRY",
  "JEWELLERY",
  "GOLD",
  "WATCHES",
  "LAMPS",
  "LAMP",
  "RUGS",
  "RUG",
  "ART",
  "PHOTOS",
  "PHOTO",
  "ALBUMS",
  "ALBUM",
  "PAPERS",
  "FILES",
  "FILE",
  "SHOES",
  "BOOTS",
  "COATS",
  "HATS",
  "BOX",
  "BOXES",
  "BIN",
  "BINS",
  "TAPE",
  "LABEL",
  "LABELS",
  "FROM",
  "FOR",
  "AND",
  "THE",
  "WITH",
];

const PACKING = new Set(PACKING_LABELS);

/**
 * Short English words that end in X. Anything else of length 3–5 ending
 * in X is treated as Seedance letter-scribble (HOX, DOX, PATX).
 */
const X_ENDING_OK = new Set([
  "BOX",
  "TAX",
  "FAX",
  "WAX",
  "SIX",
  "MIX",
  "MAX",
  "FOX",
  "LUX",
  "LOX",
  "POX",
  "SOX",
  "APEX",
  "IBEX",
  "FLUX",
  "CRUX",
  "INDEX",
  "LATEX",
  "CODEX",
  "DETOX",
  "BORAX",
  "RELAX",
  "HELIX",
]);

const COMMON_ENGLISH = new Set(
  [
    "about",
    "after",
    "again",
    "all",
    "also",
    "always",
    "another",
    "any",
    "are",
    "back",
    "because",
    "been",
    "before",
    "being",
    "both",
    "but",
    "came",
    "can",
    "come",
    "could",
    "did",
    "does",
    "done",
    "down",
    "each",
    "even",
    "every",
    "first",
    "from",
    "full",
    "good",
    "had",
    "has",
    "have",
    "her",
    "here",
    "him",
    "his",
    "into",
    "its",
    "just",
    "know",
    "last",
    "left",
    "like",
    "long",
    "look",
    "made",
    "make",
    "many",
    "more",
    "most",
    "much",
    "must",
    "name",
    "need",
    "new",
    "next",
    "not",
    "now",
    "off",
    "old",
    "one",
    "only",
    "other",
    "our",
    "out",
    "over",
    "own",
    "part",
    "place",
    "put",
    "right",
    "said",
    "same",
    "see",
    "she",
    "should",
    "some",
    "still",
    "such",
    "take",
    "than",
    "that",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "through",
    "time",
    "two",
    "under",
    "until",
    "upon",
    "used",
    "very",
    "was",
    "way",
    "well",
    "were",
    "what",
    "when",
    "where",
    "which",
    "while",
    "who",
    "will",
    "with",
    "work",
    "would",
    "year",
    "you",
    "your",
    "table",
    "chair",
    "sofa",
    "couch",
    "desk",
    "bed",
    "door",
    "window",
    "wall",
    "floor",
    "room",
    "house",
    "home",
    "family",
    "wood",
    "white",
    "black",
    "brown",
    "blue",
    "green",
    "small",
    "large",
    "open",
    "closed",
    "empty",
    "full",
    "stack",
    "stacked",
    "packed",
    "moved",
    "moving",
    "sale",
    "sold",
    "item",
    "items",
    "piece",
    "pieces",
    "value",
    "worth",
    "gold",
    "silver",
    "ring",
    "watch",
    "lamp",
    "mirror",
    "frame",
    "photo",
    "book",
    "books",
    "paper",
    "box",
    "boxes",
    "bin",
    "bins",
    "tape",
    "label",
    "kitchen",
    "fragile",
    "mahogany",
    "oak",
    "pine",
    "cherry",
    "walnut",
    "antique",
    "vintage",
    "estate",
    "jewelry",
  ].map((word) => word.toUpperCase()),
);

const COMMON_BIGRAMS = new Set([
  "TH",
  "HE",
  "IN",
  "ER",
  "AN",
  "RE",
  "ON",
  "AT",
  "EN",
  "ND",
  "TI",
  "ES",
  "OR",
  "TE",
  "OF",
  "ED",
  "IS",
  "IT",
  "AL",
  "AR",
  "ST",
  "TO",
  "NT",
  "NG",
  "SE",
  "HA",
  "AS",
  "OU",
  "IO",
  "LE",
  "VE",
  "CO",
  "ME",
  "DE",
  "HI",
  "RI",
  "RO",
  "IC",
  "NE",
  "EA",
  "RA",
  "CE",
  "LI",
  "CH",
  "LL",
  "BE",
  "MA",
  "SI",
  "OM",
  "UR",
  "CA",
  "EL",
  "LA",
  "HO",
  "US",
  "NO",
  "WA",
  "SH",
  "EC",
  "CT",
  "WH",
  "OW",
  "UN",
  "LO",
  "PE",
  "PR",
  "SS",
  "AD",
  "ET",
  "IL",
  "MO",
  "WO",
  "TA",
  "CK",
  "GH",
  "LY",
  "IM",
  "ID",
  "GE",
  "FO",
  "KI",
  "BO",
  "OK",
  "FR",
  "AG",
  "GL",
]);

const CTA_PHRASES = [
  "ready to get started",
  "get your free consultation",
  "organizinglifeservices",
  "organizing life services",
  "professional reliable trusted",
  "licensed trusted insured",
  "call today",
];

const MIN_TOKEN_LETTERS = 3;

export function tokenizeSceneText(raw: string): string[] {
  return raw
    .split(/[^A-Za-z]+/)
    .map((part) => part.trim())
    .filter((part) => part.length >= MIN_TOKEN_LETTERS);
}

export function levenshtein(a: string, b: string): number {
  if (a === b) return 0;
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;
  const prev = Array.from({ length: b.length + 1 }, (_, i) => i);
  const curr = new Array<number>(b.length + 1);
  for (let i = 0; i < a.length; i += 1) {
    curr[0] = i + 1;
    const aChar = a[i];
    for (let j = 0; j < b.length; j += 1) {
      const insert = (curr[j] ?? 0) + 1;
      const del = (prev[j + 1] ?? 0) + 1;
      const sub = (prev[j] ?? 0) + (aChar === b[j] ? 0 : 1);
      curr[j + 1] = Math.min(insert, del, sub);
    }
    for (let j = 0; j < prev.length; j += 1) {
      prev[j] = curr[j] ?? 0;
    }
  }
  return prev[b.length] ?? b.length;
}

function packingMisspellingOf(upper: string): string | undefined {
  if (PACKING.has(upper) || COMMON_ENGLISH.has(upper)) return undefined;
  if (upper.length < 4) return undefined;
  for (const label of PACKING) {
    if (label.length < 5) continue;
    const dist = levenshtein(upper, label);
    if (dist === 1) return label;
    if (dist === 2 && upper.length >= 6 && label.length >= 6) return label;
  }
  return undefined;
}

function stemInLexicon(upper: string): boolean {
  if (PACKING.has(upper) || COMMON_ENGLISH.has(upper)) return true;
  if (upper.endsWith("ES") && upper.length > 4) {
    const stem = upper.slice(0, -2);
    if (PACKING.has(stem) || COMMON_ENGLISH.has(stem)) return true;
  }
  if (upper.endsWith("S") && upper.length > 3) {
    const stem = upper.slice(0, -1);
    if (PACKING.has(stem) || COMMON_ENGLISH.has(stem)) return true;
  }
  if (upper.endsWith("ING") && upper.length > 5) {
    const stem = upper.slice(0, -3);
    if (PACKING.has(stem) || COMMON_ENGLISH.has(stem)) return true;
  }
  return false;
}

function vowelCount(upper: string): number {
  return (upper.match(/[AEIOUY]/g) ?? []).length;
}

function hasCommonBigram(upper: string): boolean {
  for (let i = 0; i < upper.length - 1; i += 1) {
    if (COMMON_BIGRAMS.has(upper.slice(i, i + 2))) return true;
  }
  return false;
}

function looksLikeEnglish(upper: string): boolean {
  const vowels = vowelCount(upper);
  if (vowels === 0) return false;
  if (vowels / upper.length < 0.18) return false;
  if (/[BCDFGHJKLMNPQRSTVWXZ]{5,}/.test(upper)) return false;
  if (/(.)\1{2,}/.test(upper)) return false;
  if (upper.length <= 5 && upper.endsWith("X") && !X_ENDING_OK.has(upper)) {
    return false;
  }
  return hasCommonBigram(upper);
}

export function classifyToken(token: string): ClassifiedToken {
  const trimmed = token.trim();
  if (trimmed.length < MIN_TOKEN_LETTERS || !/^[A-Za-z]+$/.test(trimmed)) {
    return { token: trimmed, verdict: "ignored", reason: "too short or non-letters" };
  }
  const upper = trimmed.toUpperCase();

  if (upper.includes("ORGANIZINGLIFESERVICES") || upper === "ORGANIZINGLIFESERVICES") {
    return { token: trimmed, verdict: "cta", reason: "OLS URL/lockup in the body" };
  }

  if (stemInLexicon(upper)) {
    return { token: trimmed, verdict: "ok", reason: "lexicon" };
  }

  const near = packingMisspellingOf(upper);
  if (near) {
    return {
      token: trimmed,
      verdict: "misspelling",
      reason: `near ${near}`,
    };
  }

  if (upper.length <= 5 && upper.endsWith("X") && !X_ENDING_OK.has(upper)) {
    return { token: trimmed, verdict: "gibberish", reason: "fake X-ending label" };
  }

  if (vowelCount(upper) === 0) {
    return { token: trimmed, verdict: "gibberish", reason: "no vowels" };
  }

  if (/[BCDFGHJKLMNPQRSTVWXZ]{5,}/.test(upper)) {
    return { token: trimmed, verdict: "gibberish", reason: "consonant cluster" };
  }

  if (looksLikeEnglish(upper)) {
    return { token: trimmed, verdict: "ok", reason: "english-like" };
  }

  return { token: trimmed, verdict: "gibberish", reason: "not English" };
}

function findCtaPhrases(raw: string): string[] {
  const compact = raw.toLowerCase().replace(/[^a-z0-9]+/g, " ").replace(/\s+/g, " ").trim();
  const glued = compact.replace(/\s+/g, "");
  const hits: string[] = [];
  for (const phrase of CTA_PHRASES) {
    const needle = phrase.replace(/\s+/g, "");
    if (compact.includes(phrase) || glued.includes(needle)) {
      hits.push(phrase);
    }
  }
  if (/\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b/.test(raw)) {
    hits.push("phone number");
  }
  return hits;
}

export function classifySceneText(raw: string): SceneTextReport {
  const notes: string[] = [];
  const tokens: ClassifiedToken[] = [];
  const ctaHits = findCtaPhrases(raw);
  for (const phrase of ctaHits) {
    const token: ClassifiedToken = {
      token: phrase,
      verdict: "cta",
      reason: "CTA/lockup copy in a body frame",
    };
    tokens.push(token);
    notes.push(`CTA copy in body: ${phrase}`);
  }

  for (const word of tokenizeSceneText(raw)) {
    tokens.push(classifyToken(word));
  }

  const failures = tokens.filter(
    (token) =>
      token.verdict === "gibberish" ||
      token.verdict === "misspelling" ||
      token.verdict === "cta",
  );
  for (const failure of failures) {
    if (failure.verdict === "cta") continue;
    notes.push(`${failure.verdict}: ${failure.token}${failure.reason ? ` (${failure.reason})` : ""}`);
  }

  return {
    pass: failures.length === 0,
    tokens,
    failures,
    notes,
  };
}
