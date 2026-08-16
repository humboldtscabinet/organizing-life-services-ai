/**
 * Contracts for the multi-agent layer.
 *
 * SceneTextQaAgent is wired in scripts/reframe-ad.ts after Seedance
 * returns a body clip and before ffmpeg replaces the last 3s with the
 * Shopify CTA. A fail does not retry generation — Seevio credits are
 * already spent. PromptEngineer, VariantFactory, and AssetManager are
 * not wired yet.
 */

import type {
  AspectRatio,
  GenerateAdOptions,
  GenerateAdResult,
} from "../types.ts";

/** Rewrites a creative brief before framing is appended. */
export interface PromptEngineer {
  refine(
    prompt: string,
    context: { aspectRatio?: AspectRatio; brandNotes?: string },
  ): Promise<string> | string;
}

export type QaVerdict = {
  pass: boolean;
  notes: string[];
  aspectRatio: AspectRatio;
};

/** Reviews a generated clip (duration, CTA hold, framing compliance). */
export interface QaAgent {
  review(result: GenerateAdResult): Promise<QaVerdict> | QaVerdict;
}

/** Spins a base brief into prompt / scene variants. */
export interface VariantFactory {
  variants(
    base: GenerateAdOptions,
    count: number,
  ): Promise<GenerateAdOptions[]> | GenerateAdOptions[];
}

export type StoredAsset = {
  id: string;
  aspectRatio: AspectRatio;
  path?: string;
  url?: string;
};

/** Persists finished creatives (local disk, Drive, GCS, Ads asset library). */
export interface AssetManager {
  store(result: GenerateAdResult): Promise<StoredAsset> | StoredAsset;
}
